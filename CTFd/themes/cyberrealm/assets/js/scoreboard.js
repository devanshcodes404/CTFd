import Alpine from "alpinejs";
import CTFd from "./index";

import {
  getOption,
} from "./utils/graphs/echarts/scoreboard";

import {
  embed,
} from "./utils/graphs/echarts";


window.Alpine = Alpine;
window.CTFd = CTFd;


/* =========================================
   SCOREBOARD POLLING
========================================= */

const scoreboardUpdateInterval =
  window.scoreboardUpdateInterval || 300000;


/* =========================================
   CYBERREALM RANK
========================================= */

function getPlayerRank(level) {

  if (level >= 50) {
    return "CYBER LEGEND";
  }

  if (level >= 30) {
    return "SHADOW AGENT";
  }

  if (level >= 20) {
    return "ELITE";
  }

  if (level >= 10) {
    return "SPECIALIST";
  }

  if (level >= 5) {
    return "OPERATIVE";
  }

  return "RECRUIT";
}


/* =========================================
   SCOREBOARD DETAIL
========================================= */

Alpine.data(
  "ScoreboardDetail",
  () => ({

    data: {},

    standings: [],

    show: true,

    activeBracket: null,


    /* -----------------------------------------
       UPDATE
    ----------------------------------------- */

    async update() {

      try {

        const [
          detail,
          standings,
        ] = await Promise.all([

          CTFd.pages.scoreboard
            .getScoreboardDetail(
              10,
              this.activeBracket,
            ),

          /*
           * Existing CTFd standings are still
           * required for the analytics.
           */
          CTFd.pages.scoreboard
            .getScoreboard(),

        ]);


        this.data =
          detail || {};


        this.standings =
          standings || [];


        const optionMerge =
          window.scoreboardChartOptions;


        const option =
          getOption(
            CTFd.config.userMode,
            this.data,
            optionMerge,
          );


        if (
          this.$refs.scoregraph
        ) {

          embed(
            this.$refs.scoregraph,
            option,
          );

        }


        this.show =
          Object.keys(
            this.data,
          ).length > 0;


      } catch (error) {

        console.error(
          "[CyberRealm] Scoreboard detail failed:",
          error,
        );


        this.data = {};

        this.standings = [];

        this.show = false;

      }

    },


    /* -----------------------------------------
       ANALYTICS
    ----------------------------------------- */

    getVisibleAnalyticsStandings() {

      return this.standings.filter(
        (standing) =>
          this.activeBracket === null ||
          standing.bracket_id ==
            this.activeBracket,
      );

    },


    getParticipantCount() {

      return this
        .getVisibleAnalyticsStandings()
        .length;

    },


    getHighestScore() {

      const standings =
        this.getVisibleAnalyticsStandings();


      if (
        standings.length === 0
      ) {

        return 0;

      }


      return Math.max(
        ...standings.map(
          (standing) =>
            Number(
              standing.score || 0,
            ),
        ),
      );

    },


    getAverageScore() {

      const standings =
        this.getVisibleAnalyticsStandings();


      if (
        standings.length === 0
      ) {

        return 0;

      }


      const total =
        standings.reduce(
          (
            sum,
            standing,
          ) =>
            sum +
            Number(
              standing.score || 0,
            ),
          0,
        );


      return Math.round(
        total /
        standings.length,
      );

    },


    /* -----------------------------------------
       INIT
    ----------------------------------------- */

    async init() {

      await this.update();


      setInterval(
        () => {

          this.update();

        },
        scoreboardUpdateInterval,
      );

    },

  }),
);


/* =========================================
   SCOREBOARD LIST
========================================= */

Alpine.data(
  "ScoreboardList",
  () => ({

    standings: [],

    brackets: [],

    activeBracket: null,

    search: "",

    loading: true,


    /* -----------------------------------------
       LOAD LEADERBOARD
    ----------------------------------------- */

    async update() {

      this.loading =
        true;


      try {

        /*
         * CTFd brackets are still managed
         * by the CTFd API.
         */

        this.brackets =
          await CTFd.pages.scoreboard
            .getBrackets(
              CTFd.config.userMode,
            );


        /*
         * ONE request for both:
         *
         * - CTFd score
         * - CyberRealm XP
         * - level
         * - rank
         * - streak
         */

        const response =
          await fetch(
            "/api/v1/esecurityin/leaderboard",
            {
              headers: {
                Accept:
                  "application/json",
              },
            },
          );


        if (!response.ok) {

          throw new Error(
            `Leaderboard HTTP ${response.status}`,
          );

        }


        const data =
          await response.json();


        this.standings =
          data.standings || [];


      } catch (error) {

        console.error(
          "[CyberRealm] Scoreboard loading failed:",
          error,
        );


        this.standings = [];


      } finally {

        this.loading =
          false;

      }

    },


    /* -----------------------------------------
       FILTER
    ----------------------------------------- */

    getVisibleStandings() {

      const query =
        this.search
          .trim()
          .toLowerCase();


      return this.standings

        .filter(
          (standing) =>
            this.activeBracket === null ||
            standing.bracket_id ==
              this.activeBracket,
        )

        .filter(
          (standing) =>
            !query ||
            (
              standing.name || ""
            )
              .toLowerCase()
              .includes(query),
        );

    },


    /* -----------------------------------------
       CURRENT USER
    ----------------------------------------- */

    isCurrentUser(
      standing,
    ) {

      return (
        Number(
          standing.account_id,
        ) ===
        Number(
          window.init?.userId,
        )
      );

    },


    getCurrentUserStanding() {

      return this.standings.find(
        (standing) =>
          this.isCurrentUser(
            standing,
          ),
      );

    },


    getCurrentUserNeighbors() {

      const current =
        this.getCurrentUserStanding();


      if (!current) {

        return {
          above: null,
          below: null,
        };

      }


      const index =
        this.standings.findIndex(
          (standing) =>
            Number(
              standing.account_id,
            ) === Number(
              current.account_id,
            ),
        );


      return {
        above:
          index > 0
            ? this.standings[index - 1]
            : null,

        below:
          index >= 0 &&
          index < this.standings.length - 1
            ? this.standings[index + 1]
            : null,
      };

    },


    /* -----------------------------------------
       DISPLAY RANK
    ----------------------------------------- */

    getDisplayRank(
      standing,
    ) {

      /*
       * Preserve CTFd's actual
       * scoreboard position.
       */

      if (
        typeof standing.pos ===
        "number"
      ) {

        return standing.pos;

      }


      /*
       * Fallback.
       */

      const visible =
        this.getVisibleStandings();


      const index =
        visible.findIndex(
          (item) =>
            item.account_id ===
            standing.account_id,
        );


      return index + 1;

    },


    /* -----------------------------------------
       INIT
    ----------------------------------------- */

    async init() {

      this.$watch(
        "activeBracket",
        () => {

          this.$dispatch(
            "bracket-change",
            this.activeBracket,
          );

        },
      );


      await this.update();


      this.$nextTick(
        () => {

          const currentUser =
            document.querySelector(
              ".current-user",
            );


          if (
            currentUser
          ) {

            currentUser.scrollIntoView({
              behavior: "smooth",
              block: "center",
            });

          }

        },
      );


      setInterval(
        () => {

          this.update();

        },
        scoreboardUpdateInterval,
      );

    },

  }),
);


Alpine.start();