import Alpine from "alpinejs";
import CTFd from "./index";


Alpine.data(
  "CyberRealmDashboard",
  () => ({

    /* =========================================
       PLAYER PROFILE
    ========================================== */

    profile: {

      xp: 0,

      level: 1,

      rank: "RECRUIT",

      xpPerLevel: 500,

      xpIntoLevel: 0,

      xpToNext: 500,

      progress: 0,

      streak: 0,

      longestStreak: 0,

      totalSolves: 0,

      achievementsUnlocked: 0,

      achievementsTotal: 0,

    },


    /* =========================================
       DATA
    ========================================== */

    recentSolves: [],

    missions: {
      daily: [],
      weekly: [],
      special: [],
    },

    missionCategories: [
      { key: "daily", label: "DAILY MISSIONS" },
      { key: "weekly", label: "WEEKLY MISSIONS" },
      { key: "special", label: "SPECIAL MISSIONS" },
    ],

    achievements: [],

    sectionStatus: {
      profile: "loading",
      solves: "loading",
      dailyObjectives: "loading",
    },

    missionStatus: {
      daily: "loading",
      weekly: "loading",
      special: "loading",
    },

    dailyObjectives: [],

    loading: false,

    initialized: false,

    async loadSection(name, loader) {
      this.sectionStatus[name] = "loading";

      try {
        await loader();
        this.sectionStatus[name] = "loaded";
      } catch (error) {
        console.error(`[CyberRealm] Failed to load ${name}:`, error);
        this.sectionStatus[name] = "error";
      }
    },

    async loadMissions() {
      await Promise.all(
        this.missionCategories.map(async ({ key }) => {
          this.missionStatus[key] = "loading";

          try {
            const response = await fetch(
              `/api/v1/esecurityin/missions?type=${key}`,
              {
                credentials: "same-origin",
                headers: {
                  Accept: "application/json",
                },
              },
            );

            if (!response.ok) {
              throw new Error(`Mission API returned ${response.status}`);
            }

            const data = await response.json();
            if (!Array.isArray(data.missions)) {
              throw new Error("Mission API returned an invalid mission list");
            }

            this.missions[key] = data.missions;
            this.missionStatus[key] = "loaded";
          } catch (error) {
            console.error(
              `[CyberRealm] Failed to load ${key} missions:`,
              error,
            );
            this.missionStatus[key] = "error";
          }
        }),
      );
    },

    /* =========================================
       INITIALIZE
    ========================================== */

    async init() {

      /*
       * Protection against accidental
       * duplicate initialization.
       */

      if (this.initialized) {

        console.warn(
          "[CyberRealm] Dashboard already initialized. Skipping duplicate init.",
        );

        return;

      }


      this.initialized = true;


      if (
        !window.init ||
        !window.init.userId
      ) {

        return;

      }


      if (this.loading) {

        return;

      }


      this.loading = true;


      try {

        await Promise.all([
          this.loadSection("profile", () => this.loadProfile()),
          this.loadSection("solves", () => this.loadRecentSolves()),
          this.loadSection(
            "dailyObjectives",
            () => this.loadDailyObjectives(),
          ),
          this.loadMissions(),
        ]);

      } finally {

        this.loading = false;

      }

    },


    /* =========================================
       LOAD PROFILE
    ========================================== */

    async loadProfile() {

      const userId =
        window.init.userId;


      const response =
        await fetch(
          `/api/v1/esecurityin/profile/${userId}`,
          {
            headers: {
              Accept:
                "application/json",
            },
          },
        );


      if (!response.ok) {

        throw new Error(
          `Profile HTTP ${response.status}`,
        );

      }


      const data =
        await response.json();


      console.log(
        "[CyberRealm] Dashboard profile:",
        data,
      );


      const progression =
        data.progression || {};


      const achievements =
        data.achievements || {};

      if (!data.progression || !Array.isArray(achievements.items)) {
        throw new Error("Profile API returned invalid dashboard data");
      }


      const XP_PER_LEVEL =
        500;


      const xp =
        Number(
          progression.xp || 0,
        );


      const level =
        Number(
          progression.level || 1,
        );


      const xpIntoLevel =
        xp %
        XP_PER_LEVEL;


      const progress =
        Number(
          (
            (
              xpIntoLevel /
              XP_PER_LEVEL
            ) *
            100
          ).toFixed(1),
        );


      const xpToNext =
        XP_PER_LEVEL -
        xpIntoLevel;


      this.profile = {

        xp,

        level,

        rank:
          this.getPlayerRank(
            level,
          ),

        xpPerLevel:
          XP_PER_LEVEL,

        xpIntoLevel,

        xpToNext,

        progress,

        streak:
          Number(
            progression.streak || 0,
          ),

        longestStreak:
          Number(
            progression.longest_streak || 0,
          ),

        totalSolves:
          Number(
            progression.total_solves || 0,
          ),

        achievementsUnlocked:
          Number(
            achievements.unlocked || 0,
          ),

        achievementsTotal:
          Number(
            achievements.total || 0,
          ),

      };


      this.achievements = achievements.items.map((achievement) =>
        this.enrichAchievementProgress(achievement, {
          xp,
          level,
          streak: Number(progression.streak || 0),
          totalSolves: Number(progression.total_solves || 0),
          totalMissions: Number(progression.total_missions || 0),
        }),
      );

    },

    enrichAchievementProgress(achievement, progression) {
      const requirementValues = {
        total_solves: progression.totalSolves,
        streak: progression.streak,
        level: progression.level,
        total_xp: progression.xp,
        total_missions: progression.totalMissions,
      };
      const current = requirementValues[achievement.requirement_type] || 0;
      const target = achievement.requirement_value || 1;

      return {
        ...achievement,
        progressCurrent: Math.min(current, target),
        progressTarget: target,
        remaining: Math.max(0, target - current),
        progressPercent: Math.min(
          100,
          Number(((current / target) * 100).toFixed(1)),
        ),
      };

    },


    /* =========================================
       LOAD RECENT SOLVES
    ========================================== */

    async loadRecentSolves() {

      const solves =
        await CTFd.pages.users
          .userSolves(
            "me",
          );

      if (!solves.success || !Array.isArray(solves.data)) {
        throw new Error("Solve API returned invalid dashboard data");
      }

      this.recentSolves =
        solves.data
          .slice(
            0,
            5,
          )
          .map(
            (
              solve,
            ) => ({

              challenge_id:
                solve.challenge_id,

              challenge_name:
                solve.challenge?.name ||
                "Challenge",

              category:
                solve.challenge?.category ||
                "Unknown",

              points:
                solve.challenge?.value ||
                0,

              date:
                solve.date,

            }),
          );

    },


    /* =========================================
       LOAD DAILY OBJECTIVES
    ========================================== */

    async loadDailyObjectives() {

      const userId =
        window.init.userId;


      const response =
        await fetch(
          `/api/v1/esecurityin/user/${userId}/daily-objectives`,
          {
            headers: {
              Accept:
                "application/json",
            },
          },
        );


      if (!response.ok) {

        throw new Error(
          `Daily objectives HTTP ${response.status}`,
        );

      }


      const data =
        await response.json();

      if (!Array.isArray(data.objectives)) {
        throw new Error("Daily objectives API returned an invalid list");
      }

      this.dailyObjectives =
        data.objectives;

    },


    /* =========================================
       PLAYER RANK
    ========================================== */

    getPlayerRank(
      level,
    ) {

      if (
        level >= 50
      ) {

        return "CYBER LEGEND";

      }


      if (
        level >= 30
      ) {

        return "SHADOW AGENT";

      }


      if (
        level >= 20
      ) {

        return "ELITE";

      }


      if (
        level >= 10
      ) {

        return "SPECIALIST";

      }


      if (
        level >= 5
      ) {

        return "OPERATIVE";

      }


      return "RECRUIT";

    },

  }),
);


/*
 * IMPORTANT:
 *
 * Do NOT call Alpine.start() here.
 *
 * page.js is responsible for starting Alpine.
 */