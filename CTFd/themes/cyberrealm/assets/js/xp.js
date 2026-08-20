/* =========================================
   CYBERREALM XP SYSTEM
========================================= */

if (window.__CYBERREALM_XP_INITIALIZED__) {

  console.warn(
    "[CyberRealm] XP system already initialized. Skipping duplicate initialization.",
  );

} else {

  window.__CYBERREALM_XP_INITIALIZED__ = true;


  let currentXP = null;

  let currentLevel = null;


  let achievementInitialized = false;

  let knownAchievementIds =
    new Set();


  let achievementQueue = [];

  let achievementPopupActive =
    false;

  let achievementCollectionInitialized =
    false;

  let playerAchievements = [];


  /* =========================================
     SOUND HELPERS
  ========================================== */

  function playCyberSound(
    name,
  ) {

    if (
      window.CyberSound &&
      typeof window.CyberSound.play ===
        "function"
    ) {

      window.CyberSound.play(
        name,
      );

    }

  }


async function fetchCyberRealmProfile() {

  if (
    !window.init ||
    !window.init.userId
  ) {
    return;
  }


  const userId =
    window.init.userId;


  try {

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
      "[CyberRealm] Profile:",
      data,
    );


    /* =========================================
       PLAYER PROGRESSION
    ========================================== */

    updatePlayerXP(
      data.progression || {},
    );


    /* =========================================
       ACHIEVEMENTS
    ========================================== */

    const achievements =
      data.achievements || {};


    const achievementItems =
      achievements.items || [];


    /* -----------------------------------------
       Newly unlocked achievements
    ----------------------------------------- */

    if (
      !achievementInitialized
    ) {

      /*
       * Establish the baseline.
       *
       * Existing achievements should not
       * trigger a popup on page load.
       */

      knownAchievementIds =
        new Set(
          achievementItems
            .filter(
              (achievement) =>
                achievement.unlocked === true,
            )
            .map(
              (achievement) =>
                achievement.id,
            ),
        );


      achievementInitialized =
        true;

    } else {

      /*
       * Detect achievements that were not
       * present in the previous profile.
       */

      for (
        const achievement
        of achievementItems
      ) {

        if (
          achievement.unlocked !== true
        ) {

          continue;

        }


        if (
          !knownAchievementIds.has(
            achievement.id,
          )
        ) {

          knownAchievementIds.add(
            achievement.id,
          );


          console.log(
            "[CyberRealm] ACHIEVEMENT UNLOCKED:",
            achievement.name,
          );


          playCyberSound(
            "achievement",
          );


          queueAchievementPopup(
            achievement,
          );

        }

      }

    }


    /* =========================================
       ACHIEVEMENT COLLECTION
    ========================================== */

    playerAchievements =
      achievementItems;


    updateAchievementCounter(
      achievements.unlocked || 0,
      achievements.total || 0,
    );


    if (
      !achievementCollectionInitialized
    ) {

      createAchievementCollection();

      achievementCollectionInitialized =
        true;

    }


    renderAchievementCollection();


  } catch (error) {

    console.error(
      "[CyberRealm] Failed to fetch profile:",
      error,
    );

  }

}


  /* =========================================
     ACHIEVEMENT COUNTER
  ========================================== */

  function updateAchievementCounter(
    unlocked,
    total,
  ) {

    const counter =
      document.getElementById(
        "esecurityin-achievement-counter",
      );


    if (!counter) {

      return;

    }


    counter.textContent =
      `🏆 ${unlocked} / ${total}`;

  }


  /* =========================================
     CREATE ACHIEVEMENT COLLECTION
  ========================================== */

  function createAchievementCollection() {

    const hud =
      document.getElementById(
        "esecurityin-xp-hud",
      );


    if (!hud) {

      console.error(
        "[CyberRealm] XP HUD not found.",
      );


      return;

    }


    if (
      document.getElementById(
        "esecurityin-achievement-counter",
      )
    ) {

      return;

    }


    const counter =
      document.createElement(
        "button",
      );


    counter.id =
      "esecurityin-achievement-counter";


    counter.type =
      "button";


    counter.className =
      "esecurityin-achievement-counter";


    counter.textContent =
      "🏆 0 / 0";


    counter.addEventListener(
      "click",
      () => {

        toggleAchievementCollection();

      },
    );


    hud.appendChild(
      counter,
    );


    const panel =
      document.createElement(
        "div",
      );


    panel.id =
      "esecurityin-achievement-panel";


    panel.className =
      "esecurityin-achievement-panel";


    panel.innerHTML = `
      <div class="achievement-panel-header">

        <div>

          <div class="achievement-panel-title">
            ACHIEVEMENTS
          </div>

          <div
            id="achievement-panel-progress"
            class="achievement-panel-progress"
          >
            0 / 0 UNLOCKED
          </div>

        </div>


        <button
          id="achievement-panel-close"
          class="achievement-panel-close"
          type="button"
        >
          ×
        </button>

      </div>


      <div
        id="achievement-panel-list"
        class="achievement-panel-list"
      ></div>
    `;


    document.body.appendChild(
      panel,
    );


    const closeButton =
      document.getElementById(
        "achievement-panel-close",
      );


    if (closeButton) {

      closeButton.addEventListener(
        "click",
        () => {

          closeAchievementCollection();

        },
      );

    }

  }


  /* =========================================
     RENDER ACHIEVEMENT COLLECTION
  ========================================== */

  function renderAchievementCollection() {

    const list =
      document.getElementById(
        "achievement-panel-list",
      );


    const progress =
      document.getElementById(
        "achievement-panel-progress",
      );


    if (!list) {

      return;

    }


    const unlockedCount =
      playerAchievements.filter(
        (
          achievement,
        ) =>
          achievement.unlocked,
      ).length;


    if (progress) {

      progress.textContent =
        `${unlockedCount} / ${playerAchievements.length} UNLOCKED`;

    }


    list.innerHTML =
      playerAchievements
        .map(
          (
            achievement,
          ) => {

            const stateClass =
              achievement.unlocked
                ? "unlocked"
                : "locked";


            const icon =
              achievement.unlocked
                ? achievement.icon
                : "🔒";


            return `
              <div
                class="
                  achievement-card
                  ${stateClass}
                "
              >

                <div class="achievement-card-icon">
                  ${icon}
                </div>

                <div class="achievement-card-body">

                  <div class="achievement-card-name">
                    ${achievement.name}
                  </div>

                  <div class="achievement-card-description">
                    ${achievement.description}
                  </div>

                  <div class="achievement-card-reward">
                    +${achievement.xp_reward} XP
                  </div>

                </div>

              </div>
            `;

          },
        )
        .join("");

  }


  /* =========================================
     TOGGLE ACHIEVEMENT COLLECTION
  ========================================== */

  function toggleAchievementCollection() {

    const panel =
      document.getElementById(
        "esecurityin-achievement-panel",
      );


    if (!panel) {

      return;

    }


    panel.classList.toggle(
      "show",
    );

  }


  /* =========================================
     CLOSE ACHIEVEMENT COLLECTION
  ========================================== */

  function closeAchievementCollection() {

    const panel =
      document.getElementById(
        "esecurityin-achievement-panel",
      );


    if (!panel) {

      return;

    }


    panel.classList.remove(
      "show",
    );

  }


  /* =========================================
     PLAYER RANK
  ========================================== */

  function getPlayerRank(
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

  }


  /* =========================================
     UPDATE PLAYER XP
  ========================================== */

  function updatePlayerXP(
    data,
  ) {

    const xpElement =
      document.getElementById(
        "esecurityin-xp",
      );


    const levelElement =
      document.getElementById(
        "esecurityin-level",
      );


    const rankElement =
      document.getElementById(
        "esecurityin-rank",
      );


    const nextLevelElement =
      document.getElementById(
        "esecurityin-next-level",
      );


    const currentXPElement =
      document.getElementById(
        "esecurityin-xp-current",
      );


    const streakElement =
      document.getElementById(
        "esecurityin-streak",
      );


    const xpBar =
      document.getElementById(
        "esecurityin-xp-bar",
      );


    const XP_PER_LEVEL =
      500;


    const xpIntoLevel =
      data.xp %
      XP_PER_LEVEL;


    const progress =
      (
        xpIntoLevel /
        XP_PER_LEVEL
      ) * 100;


    const nextLevelXP =
      XP_PER_LEVEL -
      xpIntoLevel;


    /*
     * First API response.
     *
     * Establish baseline without
     * playing any sound.
     */

    if (
      currentXP === null
    ) {

      currentXP =
        data.xp;


      currentLevel =
        data.level;

    }


    /*
     * Detect XP gain.
     */

    if (
      data.xp >
      currentXP
    ) {

      const gainedXP =
        data.xp -
        currentXP;


      playCyberSound(
        "xp",
      );


      showXPGain(
        gainedXP,
      );

    }


    /*
     * Detect level-up.
     */

    if (
  currentLevel !== null &&
  data.level > currentLevel
) {

  console.log(
    `[CyberRealm] LEVEL UP: ${currentLevel} → ${data.level}`,
  );

  playCyberSound(
    "levelup",
  );

  showLevelUp(
    data.level,
  );

}


    /*
     * Update total XP.
     */

    if (xpElement) {

      xpElement.textContent =
        `${data.xp} XP`;

    }


    /*
     * Update level.
     */

    if (levelElement) {

      levelElement.textContent =
        `LEVEL ${data.level}`;

    }


    /*
     * Update rank.
     */

    if (rankElement) {

      rankElement.textContent =
        getPlayerRank(
          data.level,
        );

    }


    /*
     * Update next-level information.
     */

    if (nextLevelElement) {

      nextLevelElement.textContent =
        `${nextLevelXP} XP TO NEXT LEVEL`;

    }


    /*
     * Update current-level XP.
     */

    if (currentXPElement) {

      currentXPElement.textContent =
        `${xpIntoLevel} / ${XP_PER_LEVEL} XP`;

    }


    /*
     * Update streak.
     */

    if (streakElement) {

      const streak =
        data.streak || 0;


      streakElement.textContent =
        `🔥 ${streak} DAY STREAK`;

    }


    /*
     * Animate progress bar.
     */

    if (xpBar) {

      requestAnimationFrame(
        () => {

          xpBar.style.width =
            `${progress}%`;

        },
      );

    }


    /*
     * Store latest state for
     * the next poll.
     */

    currentXP =
      data.xp;


    currentLevel =
      data.level;

  }


  /* =========================================
     XP GAIN ANIMATION
  ========================================== */

  function showXPGain(
    amount,
  ) {

    const popup =
      document.createElement(
        "div",
      );


    popup.className =
      "esecurityin-xp-gain";


    popup.textContent =
      `+${amount} XP`;


    document.body.appendChild(
      popup,
    );


    requestAnimationFrame(
      () => {

        popup.classList.add(
          "show",
        );

      },
    );


    setTimeout(
      () => {

        popup.remove();

      },
      1800,
    );

  }


  /* =========================================
     LEVEL-UP ANIMATION
  ========================================== */

  function showLevelUp(
    level,
  ) {

    const existing =
      document.querySelector(
        ".esecurityin-level-up",
      );


    if (existing) {

      existing.remove();

    }


    const overlay =
      document.createElement(
        "div",
      );


    overlay.className =
      "esecurityin-level-up";


    overlay.innerHTML = `
      <div class="level-up-content">

        <div class="level-up-icon">
          ⚡
        </div>

        <div class="level-up-title">
          SYSTEM UPGRADE
        </div>

        <div class="level-up-level">
          LEVEL ${level}
        </div>

      </div>
    `;


    document.body.appendChild(
      overlay,
    );


    requestAnimationFrame(
      () => {

        overlay.classList.add(
          "show",
        );

      },
    );


    setTimeout(
      () => {

        overlay.classList.remove(
          "show",
        );

      },
      2200,
    );


    setTimeout(
      () => {

        overlay.remove();

      },
      2700,
    );

  }


  /* =========================================
     QUEUE ACHIEVEMENT POPUP
  ========================================== */

  function queueAchievementPopup(
    achievement,
  ) {

    achievementQueue.push(
      achievement,
    );


    processAchievementQueue();

  }


  /* =========================================
     PROCESS ACHIEVEMENT QUEUE
  ========================================== */

  function processAchievementQueue() {

    if (
      achievementPopupActive
    ) {

      return;

    }


    if (
      achievementQueue.length ===
      0
    ) {

      return;

    }


    const achievement =
      achievementQueue.shift();


    showAchievementUnlocked(
      achievement,
    );

  }


  /* =========================================
     ACHIEVEMENT UNLOCKED
  ========================================== */

  function showAchievementUnlocked(
    achievement,
  ) {

    achievementPopupActive =
      true;


    /*
     * Achievement sound.
     *
     * It is played once for each
     * newly detected achievement.
     */


    const popup =
      document.createElement(
        "div",
      );


    popup.className =
      "esecurityin-achievement-popup";


    popup.innerHTML = `
      <div class="achievement-popup-icon">
        ${achievement.icon}
      </div>

      <div class="achievement-popup-body">

        <div class="achievement-popup-label">
          ACHIEVEMENT UNLOCKED
        </div>

        <div class="achievement-popup-name">
          ${achievement.name}
        </div>

        <div class="achievement-popup-description">
          ${achievement.description}
        </div>

        <div class="achievement-popup-reward">
          +${achievement.xp_reward} XP
        </div>

      </div>
    `;


    document.body.appendChild(
      popup,
    );


    requestAnimationFrame(
      () => {

        popup.classList.add(
          "show",
        );

      },
    );


    /*
     * Hold notification on screen.
     */

    setTimeout(
      () => {

        popup.classList.remove(
          "show",
        );

      },
      4000,
    );


    /*
     * Remove it and process
     * the next achievement.
     */

    setTimeout(
      () => {

        popup.remove();


        achievementPopupActive =
          false;


        processAchievementQueue();

      },
      4500,
    );

  }


  /* =========================================
     REMOVE DUPLICATE XP HUDS
  ========================================== */

  function removeDuplicateXPHuds() {

    const huds =
      document.querySelectorAll(
        "#esecurityin-xp-hud",
      );


    if (
      huds.length <= 1
    ) {

      return;

    }


    console.warn(
      `[CyberRealm] Removing ${huds.length - 1} duplicate XP HUD(s).`,
    );


    huds.forEach(
      (
        hud,
        index,
      ) => {

        if (
          index > 0
        ) {

          hud.remove();

        }

      },
    );

  }


  /* =========================================
     INITIAL PAGE LOAD
  ========================================== */

  document.addEventListener(
    "DOMContentLoaded",
    () => {

      removeDuplicateXPHuds();

      fetchCyberRealmProfile();

    },
  );


  /* =========================================
     KEEP XP + ACHIEVEMENTS SYNCHRONIZED
  ========================================== */

  setInterval(
    () => {

      fetchCyberRealmProfile();

    },
    5000,
  );

}