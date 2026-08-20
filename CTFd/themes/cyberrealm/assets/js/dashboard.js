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

    recentAchievements: [],

    dailyObjectives: [],


    loading: false,


    initialized: false,


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

          this.loadProfile(),

          this.loadRecentSolves(),

          this.loadDailyObjectives(),

        ]);

      } catch (error) {

        console.error(
          "[CyberRealm] Dashboard initialization failed:",
          error,
        );

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


      /*
       * Only show unlocked achievements
       * in the dashboard.
       */

      this.recentAchievements =
        (
          achievements.items || []
        )
          .filter(
            (
              achievement,
            ) =>
              achievement.unlocked ===
              true,
          )
          .slice(
            0,
            3,
          );

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


      this.recentSolves =
        (
          solves.data || []
        )
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


      this.dailyObjectives =
        data.objectives || [];

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