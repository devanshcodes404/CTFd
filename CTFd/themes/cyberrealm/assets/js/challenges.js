import Alpine from "alpinejs";
import CTFd from "./index";

import {
  Modal,
  Tab,
  Tooltip,
} from "bootstrap";

import highlight from "./theme/highlight";
import { intl } from "./theme/times";


/* =========================================
   OPEN EXTERNAL LINKS IN NEW TAB
========================================= */

function addTargetBlank(html) {

  let dom =
    new DOMParser();

  let view =
    dom.parseFromString(
      html,
      "text/html",
    );


  let links =
    view.querySelectorAll(
      'a[href*="://"]',
    );


  links.forEach(
    (link) => {

      link.setAttribute(
        "target",
        "_blank",
      );

    },
  );


  return view
    .documentElement
    .outerHTML;
}


window.Alpine = Alpine;


/* =========================================
   CHALLENGE STORE
========================================= */

Alpine.store(
  "challenge",
  {
    data: {
      view: "",
    },
  },
);


/* =========================================
   HINT
========================================= */

Alpine.data(
  "Hint",
  () => ({

    id: null,

    html: null,


    async showHint(event) {

      if (
        event.target.open
      ) {

        let response =
          await CTFd.pages.challenge
            .loadHint(
              this.id,
            );


        if (
          response.errors
        ) {

          event.target.open =
            false;


          CTFd._functions.challenge
            .displayUnlockError(
              response,
            );


          return;
        }


        let hint =
          response.data;


        if (
          hint.content
        ) {

          this.html =
            addTargetBlank(
              hint.html,
            );

        } else {

          let answer =
            await CTFd.pages.challenge
              .displayUnlock(
                this.id,
              );


          if (answer) {

            let unlock =
              await CTFd.pages.challenge
                .loadUnlock(
                  this.id,
                );


            if (
              unlock.success
            ) {

              let response =
                await CTFd.pages.challenge
                  .loadHint(
                    this.id,
                  );


              let hint =
                response.data;


              this.html =
                addTargetBlank(
                  hint.html,
                );

            } else {

              event.target.open =
                false;


              CTFd._functions.challenge
                .displayUnlockError(
                  unlock,
                );

            }

          } else {

            event.target.open =
              false;

          }

        }

      }

    },

  }),
);


/* =========================================
   CHALLENGE MODAL
========================================= */

Alpine.data(
  "Challenge",
  () => ({

    id: null,

    next_id: null,

    submission: "",

    tab: null,

    solves: [],

    submissions: [],

    solution: null,

    response: null,

    share_url: null,

    max_attempts: 0,

    attempts: 0,

    ratingValue: 0,

    selectedRating: 0,

    ratingReview: "",

    ratingSubmitted: false,


    /* -----------------------------------------
       INIT
    ----------------------------------------- */

    init() {

      highlight();

    },


    /* -----------------------------------------
       STYLES
    ----------------------------------------- */

    getStyles() {

      let styles = {
        "modal-dialog": true,
      };


      try {

        let size =
          CTFd.config.themeSettings
            .challenge_window_size;


        switch (size) {

          case "sm":

            styles["modal-sm"] =
              true;

            break;


          case "lg":

            styles["modal-lg"] =
              true;

            break;


          case "xl":

            styles["modal-xl"] =
              true;

            break;


          default:

            break;
        }

      } catch (error) {

        console.log(
          "Error processing challenge_window_size",
        );

        console.log(
          error,
        );

      }


      return styles;

    },


    /* -----------------------------------------
       SHOW CHALLENGE
    ----------------------------------------- */

    async showChallenge() {

      new Tab(
        this.$el,
      ).show();

    },


    /* -----------------------------------------
       SHOW SOLVES
    ----------------------------------------- */

    async showSolves() {

      this.solves =
        await CTFd.pages.challenge
          .loadSolves(
            this.id,
          );


      this.solves.forEach(
        (solve) => {

          solve.date =
            intl.format(
              new Date(
                solve.date,
              ),
            );


          return solve;

        },
      );


      new Tab(
        this.$el,
      ).show();

    },


    /* -----------------------------------------
       SHOW SUBMISSIONS
    ----------------------------------------- */

    async showSubmissions() {

      let response =
        await CTFd.pages.users
          .userSubmissions(
            "me",
            this.id,
          );


      this.submissions =
        response.data;


      this.submissions.forEach(
        (submission) => {

          submission.date =
            intl.format(
              new Date(
                submission.date,
              ),
            );


          return submission;

        },
      );


      new Tab(
        this.$el,
      ).show();

    },


    /* -----------------------------------------
       SOLUTION ID
    ----------------------------------------- */

    getSolutionId() {

      let data =
        Alpine.store(
          "challenge",
        ).data;


      return data.solution_id;

    },


    /* -----------------------------------------
       SOLUTION STATE
    ----------------------------------------- */

    getSolutionState() {

      let data =
        Alpine.store(
          "challenge",
        ).data;


      return data.solution_state;

    },


    /* -----------------------------------------
       SET SOLUTION ID
    ----------------------------------------- */

    setSolutionId(
      solutionId,
    ) {

      Alpine.store(
        "challenge",
      ).data.solution_id =
        solutionId;

    },


    /* -----------------------------------------
       SHOW SOLUTION
    ----------------------------------------- */

    async showSolution() {

      let solution_id =
        this.getSolutionId();


      CTFd._functions.challenge
        .displaySolution =
        (solution) => {

          this.solution =
            solution.html;


          new Tab(
            this.$el,
          ).show();

        };


      await CTFd.pages.challenge
        .displaySolution(
          solution_id,
        );

    },


    /* -----------------------------------------
       NEXT CHALLENGE ID
    ----------------------------------------- */

    getNextId() {

      let data =
        Alpine.store(
          "challenge",
        ).data;


      return data.next_id;

    },


    /* -----------------------------------------
       NEXT CHALLENGE
    ----------------------------------------- */

    async nextChallenge() {

      let modal =
        Modal.getOrCreateInstance(
          "[x-ref='challengeWindow']",
        );


      modal._element
        .addEventListener(
          "hidden.bs.modal",
          () => {

            Alpine.nextTick(
              () => {

                this.$dispatch(
                  "load-challenge",
                  this.getNextId(),
                );

              },
            );

          },
          {
            once: true,
          },
        );


      modal.hide();

    },


    /* -----------------------------------------
       SHARE URL
    ----------------------------------------- */

    async getShareUrl() {

      let body = {
        type: "solve",

        challenge_id:
          this.id,
      };


      const response =
        await CTFd.fetch(
          "/api/v1/shares",
          {
            method: "POST",

            body:
              JSON.stringify(
                body,
              ),
          },
        );


      const data =
        await response.json();


      const url =
        data["data"]["url"];


      this.share_url =
        url;

    },


    /* -----------------------------------------
       COPY SHARE URL
    ----------------------------------------- */

    copyShareUrl() {

      navigator.clipboard
        .writeText(
          this.share_url,
        );


      let t =
        Tooltip.getOrCreateInstance(
          this.$el,
        );


      t.enable();

      t.show();


      setTimeout(
        () => {

          t.hide();

          t.disable();

        },
        2000,
      );

    },


    /* -----------------------------------------
       SUBMIT CHALLENGE
    ----------------------------------------- */

    async submitChallenge() {

      this.loading =
        true;


      this.response =
        await CTFd.pages.challenge
          .submitChallenge(
            this.id,
            this.submission,
          );


      /*
       * Anonymous users must be
       * redirected to login.
       */

      if (
        this.response.data.status ===
        "authentication_required"
      ) {

        window.location =
          `${CTFd.config.urlRoot}/login?next=${CTFd.config.urlRoot}${window.location.pathname}${window.location.hash}`;


        return;

      }


      await this.renderSubmissionResponse();


      this.loading =
        false;

    },


    /* -----------------------------------------
       SUBMISSION RESPONSE
    ----------------------------------------- */

    async renderSubmissionResponse() {

      /*
       * Correct answer
       */

      if (
        this.response.data.status ===
        "correct"
      ) {

        if (
          window.CyberSound &&
          typeof window.CyberSound.play ===
            "function"
        ) {

          window.CyberSound.play(
            "correct",
          );

        }


        this.submission =
          "";

      }


      /*
       * Incorrect answer
       */

      if (
        this.response.data.status ===
        "incorrect"
      ) {

        if (
          window.CyberSound &&
          typeof window.CyberSound.play ===
            "function"
        ) {

          window.CyberSound.play(
            "wrong",
          );

        }

      }


      /*
       * Decide whether to check
       * for the solution.
       */

      if (
        this.getSolutionId() == null
      ) {

        if (
          CTFd.pages.challenge
            .checkSolution(
              this.getSolutionState(),
              Alpine.store(
                "challenge",
              ).data,
              this.response.data.status,
            )
        ) {

          let data =
            await CTFd.pages.challenge
              .getSolution(
                this.id,
              );


          this.setSolutionId(
            data.id,
          );

        }

      }


      /*
       * Increment attempts.
       */

      if (
        this.max_attempts > 0 &&
        this.response.data.status !==
          "already_solved" &&
        this.response.data.status !==
          "ratelimited"
      ) {

        this.attempts +=
          1;

      }


      /*
       * Refresh challenge board.
       *
       * This updates solved_by_me
       * after a successful solve.
       */

      this.$dispatch(
        "load-challenges",
      );

    },


    /* -----------------------------------------
       SUBMIT RATING
    ----------------------------------------- */

    async submitRating() {

      const response =
        await CTFd.pages.challenge
          .submitRating(
            this.id,
            this.selectedRating,
            this.ratingReview,
          );


      if (
        response.value
      ) {

        this.ratingValue =
          this.selectedRating;


        this.ratingSubmitted =
          true;

      } else {

        alert(
          "Error submitting rating",
        );

      }

    },

  }),
);


/* =========================================
   CHALLENGE BOARD
========================================= */

Alpine.data(
  "ChallengeBoard",
  () => ({

    loaded: false,

    challenges: [],

    challenge: null,

    selectedCategory: null,


    /* =====================================
       INITIALIZATION
    ===================================== */

    async init() {

      this.challenges =
        await CTFd.pages.challenges
          .getChallenges();


      this.loaded =
        true;


      /*
       * Open challenge from
       * URL hash.
       */

      if (
        window.location.hash
      ) {

        let chalHash =
          decodeURIComponent(
            window.location.hash.substring(
              1,
            ),
          );


        let idx =
          chalHash.lastIndexOf(
            "-",
          );


        if (
          idx >= 0
        ) {

          let pieces = [

            chalHash.slice(
              0,
              idx,
            ),

            chalHash.slice(
              idx + 1,
            ),

          ];


          let id =
            pieces[1];


          await this.loadChallenge(
            id,
          );

        }

      }

    },


    /* =====================================
       DIFFICULTY
    ===================================== */

    getDifficulty(
      challenge,
    ) {

      const difficultyTags = [
        "easy",
        "medium",
        "hard",
        "insane",
      ];


      const tag =
        (challenge.tags || []).find(
          (item) =>
            difficultyTags.includes(
              String(
                item.value,
              )
                .trim()
                .toLowerCase(),
            ),
        );


      if (
        !tag
      ) {

        return "UNRATED";

      }


      return String(
        tag.value,
      )
        .trim()
        .toUpperCase();

    },


    /* =====================================
       XP REWARD
    ===================================== */

    getXPReward(
      challenge,
    ) {

      const points =
        Number(
          challenge.value,
        ) || 0;


      return Math.max(
        10,
        Math.floor(
          points / 2,
        ),
      );

    },


    /* =====================================
       CATEGORIES
    ===================================== */

    getCategories() {

      const categories =
        [];


      this.challenges.forEach(
        (challenge) => {

          const {
            category,
          } = challenge;


          if (
            !categories.includes(
              category,
            )
          ) {

            categories.push(
              category,
            );

          }

        },
      );


      try {

        const f =
          CTFd.config
            .themeSettings
            .challenge_category_order;


        if (
          f
        ) {

          const getSort =
            new Function(
              `return (${f})`,
            );


          categories.sort(
            getSort(),
          );

        }

      } catch (error) {

        console.log(
          "Error running challenge_category_order function",
        );

        console.log(
          error,
        );

      }


      return categories;

    },


    /* =====================================
       VISIBLE CATEGORIES
    ===================================== */

    getVisibleCategories() {

      if (
        this.selectedCategory ===
        null
      ) {

        return this.getCategories();

      }


      return this.getCategories()
        .filter(
          (category) =>
            category ===
            this.selectedCategory,
        );

    },


    /* =====================================
       CHALLENGES BY CATEGORY
    ===================================== */

    getChallenges(
      category,
    ) {

      let challenges =
        this.challenges;


      if (
        category !==
        null
      ) {

        challenges =
          this.challenges.filter(
            (challenge) =>
              challenge.category ===
              category,
          );

      }


      try {

        const f =
          CTFd.config
            .themeSettings
            .challenge_order;


        if (
          f
        ) {

          const getSort =
            new Function(
              `return (${f})`,
            );


          challenges.sort(
            getSort(),
          );

        }

      } catch (error) {

        console.log(
          "Error running challenge_order function",
        );

        console.log(
          error,
        );

      }


      return challenges;

    },


    /* =====================================
       RELOAD CHALLENGES
    ===================================== */

    async loadChallenges() {

      this.challenges =
        await CTFd.pages.challenges
          .getChallenges();

    },


    /* =====================================
       OPEN CHALLENGE
    ===================================== */

    async loadChallenge(
      challengeId,
    ) {

      /*
       * CyberRealm challenge-open sound.
       */

      if (
        window.CyberSound &&
        typeof window.CyberSound.play ===
          "function"
      ) {

        window.CyberSound.play(
          "challenge",
        );

      }


      /*
       * Small card interaction.
       */

      const card =
        document.querySelector(
          `.cyberrealm-challenge-card[value="${challengeId}"]`,
        );


      if (
        card
      ) {

        card.classList.add(
          "challenge-card-opening",
        );


        setTimeout(
          () => {

            card.classList.remove(
              "challenge-card-opening",
            );

          },
          350,
        );

      }


      /*
       * Open the real CTFd
       * challenge modal.
       */

      await CTFd.pages.challenge
        .displayChallenge(
          challengeId,
          (challenge) => {

            challenge.data.view =
              addTargetBlank(
                challenge.data.view,
              );


            Alpine.store(
              "challenge",
            ).data =
              challenge.data;


            Alpine.nextTick(
              () => {

                let modal =
                  Modal.getOrCreateInstance(
                    "[x-ref='challengeWindow']",
                  );


                modal._element
                  .addEventListener(
                    "hidden.bs.modal",
                    () => {

                      history.replaceState(
                        null,
                        null,
                        " ",
                      );

                    },
                    {
                      once: true,
                    },
                  );


                modal.show();


                history.replaceState(
                  null,
                  null,
                  `#${challenge.data.name}-${challengeId}`,
                );

              },
            );

          },
        );

    },

  }),
);


Alpine.start();