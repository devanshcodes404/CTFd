import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text

from CTFd.models import db
from tests.helpers import create_ctfd, destroy_ctfd, gen_user


@pytest.fixture
def app():
    app = create_ctfd(enable_plugins=True)
    try:
        yield app
    finally:
        destroy_ctfd(app)


def _require_mysql(app):
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if not (uri.startswith("mysql") or uri.startswith("mariadb")):
        pytest.skip("UserXP migration test requires disposable MySQL/MariaDB")


def _load_migration():
    migration_path = (
        Path(__file__).resolve().parents[3]
        / "migrations"
        / "versions"
        / "f28c4d9a6b13_add_user_xp_user_foreign_key.py"
    )
    spec = importlib.util.spec_from_file_location(
        "user_xp_foreign_key_migration", migration_path
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_user_xp_foreign_key_migration_guards_orphans_and_cascades(app):
    with app.app_context():
        _require_mysql(app)

        from CTFd.plugins.esecurityin.models import UserXP

        migration = _load_migration()
        bind = db.engine.connect()
        try:
            inspector = inspect(bind)
            model_foreign_key = next(
                foreign_key
                for foreign_key in UserXP.__table__.foreign_keys
                if foreign_key.parent.name == "user_id"
            )
            assert model_foreign_key.target_fullname == "users.id"
            assert model_foreign_key.ondelete == "CASCADE"

            user_indexes_before = {
                (tuple(index["column_names"]), index["unique"])
                for index in inspector.get_indexes("user_xp")
                if index["column_names"] == ["user_id"]
            }
            assert (("user_id",), True) in user_indexes_before

            existing_user_foreign_key = next(
                foreign_key
                for foreign_key in inspector.get_foreign_keys("user_xp")
                if foreign_key["constrained_columns"] == ["user_id"]
            )
            with Operations.context(MigrationContext.configure(bind)) as operations:
                operations.drop_constraint(
                    existing_user_foreign_key["name"],
                    "user_xp",
                    type_="foreignkey",
                )

            user = gen_user(db)
            user_id = user.id
            db.session.add(UserXP(user_id=user.id))
            db.session.commit()

            orphan_user_id = 2_000_000_000
            db.session.execute(
                text(
                    """
                    INSERT INTO user_xp
                        (user_id, xp, level, streak, longest_streak, total_solves)
                    VALUES
                        (:user_id, 0, 1, 0, 0, 0)
                    """
                ),
                {"user_id": orphan_user_id},
            )
            db.session.commit()

            with Operations.context(MigrationContext.configure(bind)):
                with pytest.raises(RuntimeError, match="No rows were deleted"):
                    migration.upgrade()

            assert (
                db.session.execute(
                    text("SELECT COUNT(*) FROM user_xp WHERE user_id = :user_id"),
                    {"user_id": orphan_user_id},
                )
                .scalar_one()
                == 1
            )

            db.session.execute(
                text("DELETE FROM user_xp WHERE user_id = :user_id"),
                {"user_id": orphan_user_id},
            )
            db.session.commit()

            bind.close()
            bind = db.engine.connect()
            remaining_orphans = bind.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM user_xp AS xp
                    LEFT JOIN users AS u ON u.id = xp.user_id
                    WHERE u.id IS NULL
                    """
                )
            ).scalar_one()
            assert remaining_orphans == 0

            with Operations.context(MigrationContext.configure(bind)):
                migration.upgrade()

            foreign_key = next(
                foreign_key
                for foreign_key in inspect(bind).get_foreign_keys("user_xp")
                if foreign_key["name"] == migration.CONSTRAINT
            )
            assert foreign_key["constrained_columns"] == ["user_id"]
            assert foreign_key["referred_table"] == "users"
            assert foreign_key["referred_columns"] == ["id"]
            assert foreign_key["options"]["ondelete"].upper() == "CASCADE"

            user_indexes_after = {
                (tuple(index["column_names"]), index["unique"])
                for index in inspect(bind).get_indexes("user_xp")
                if index["column_names"] == ["user_id"]
            }
            assert user_indexes_after == user_indexes_before

            db.session.delete(user)
            db.session.commit()
            assert (
                db.session.execute(
                    text("SELECT COUNT(*) FROM user_xp WHERE user_id = :user_id"),
                    {"user_id": user_id},
                )
                .scalar_one()
                == 0
            )

            db.session.rollback()
            with Operations.context(MigrationContext.configure(bind)):
                migration.downgrade()
            assert not any(
                foreign_key["name"] == migration.CONSTRAINT
                for foreign_key in inspect(bind).get_foreign_keys("user_xp")
            )
        finally:
            bind.close()


def test_user_xp_migration_preserves_existing_equivalent_foreign_key(app):
    with app.app_context():
        _require_mysql(app)
        migration = _load_migration()
        bind = db.engine.connect()

        legacy_constraint = "legacy_user_xp_user_id_users"
        original_constraint = None

        try:
            existing = next(
                foreign_key
                for foreign_key in inspect(bind).get_foreign_keys("user_xp")
                if migration._expected_foreign_key(foreign_key)
            )
            original_constraint = existing["name"]

            # Simulate a database with an equivalent, differently named FK.
            with Operations.context(MigrationContext.configure(bind)) as operations:
                operations.drop_constraint(
                    original_constraint,
                    "user_xp",
                    type_="foreignkey",
                )
                operations.create_foreign_key(
                    legacy_constraint,
                    "user_xp",
                    "users",
                    ["user_id"],
                    ["id"],
                    ondelete="CASCADE",
                )

            with Operations.context(MigrationContext.configure(bind)):
                migration.upgrade()

            after_upgrade = inspect(bind).get_foreign_keys("user_xp")
            assert any(
                foreign_key["name"] == legacy_constraint
                and migration._expected_foreign_key(foreign_key)
                for foreign_key in after_upgrade
            )
            assert not any(
                foreign_key["name"] == migration.CONSTRAINT
                for foreign_key in after_upgrade
            )

            with Operations.context(MigrationContext.configure(bind)):
                migration.downgrade()

            after_downgrade = inspect(bind).get_foreign_keys("user_xp")
            assert any(
                foreign_key["name"] == legacy_constraint
                and migration._expected_foreign_key(foreign_key)
                for foreign_key in after_downgrade
            )

        finally:
            try:
                # Restore the constraint name present before this test.
                if original_constraint is not None:
                    current = inspect(bind).get_foreign_keys("user_xp")

                    with Operations.context(
                        MigrationContext.configure(bind)
                    ) as operations:
                        for foreign_key in current:
                            name = foreign_key.get("name")
                            if (
                                name in {legacy_constraint, migration.CONSTRAINT}
                                and name != original_constraint
                            ):
                                operations.drop_constraint(
                                    name,
                                    "user_xp",
                                    type_="foreignkey",
                                )

                        current_names = {
                            foreign_key.get("name")
                            for foreign_key in inspect(bind).get_foreign_keys(
                                "user_xp"
                            )
                        }

                        if original_constraint not in current_names:
                            operations.create_foreign_key(
                                original_constraint,
                                "user_xp",
                                "users",
                                ["user_id"],
                                ["id"],
                                ondelete="CASCADE",
                            )
            finally:
                bind.close()