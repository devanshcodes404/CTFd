/* =========================================
   CYBERREALM SOUND ENGINE
   Web Audio API
========================================= */

(() => {
  "use strict";

  let audioContext = null;

  let masterVolume = 0.65;

  let enabled = true;


  /* =========================================
     AUDIO CONTEXT
  ========================================== */

  function getAudioContext() {
    if (!audioContext) {
      const AudioContext =
        window.AudioContext ||
        window.webkitAudioContext;

      if (!AudioContext) {
        return null;
      }

      audioContext =
        new AudioContext();
    }

    return audioContext;
  }


  async function ensureReady() {
    const context =
      getAudioContext();

    if (!context) {
      return null;
    }

    if (context.state === "suspended") {
      try {
        await context.resume();
      } catch (error) {
        console.warn(
          "[CyberRealm] Unable to resume audio:",
          error,
        );

        return null;
      }
    }

    return context;
  }


  /* =========================================
     BASIC TONE
  ========================================== */

  function tone({
    frequency = 440,
    duration = 0.08,
    volume = 1,
    type = "sine",
    startTime = 0,
    endFrequency = null,
  }) {

    const context =
      getAudioContext();

    if (!context) {
      return;
    }


    const oscillator =
      context.createOscillator();

    const gain =
      context.createGain();


    oscillator.type =
      type;


    const now =
      context.currentTime +
      startTime;


    oscillator.frequency.setValueAtTime(
      frequency,
      now,
    );


    if (endFrequency) {

      oscillator.frequency.exponentialRampToValueAtTime(
        Math.max(
          20,
          endFrequency,
        ),
        now + duration,
      );

    }


    const finalVolume =
  Math.max(
    0,
    Math.min(
      0.95,
      volume *
        masterVolume,
    ),
  );


    gain.gain.setValueAtTime(
      0.0001,
      now,
    );


    gain.gain.exponentialRampToValueAtTime(
      finalVolume,
      now + 0.008,
    );


    gain.gain.exponentialRampToValueAtTime(
      0.0001,
      now + duration,
    );


    oscillator.connect(gain);

    gain.connect(
      context.destination,
    );


    oscillator.start(now);

    oscillator.stop(
      now + duration + 0.02,
    );
  }


  /* =========================================
     SOUND PROFILES
  ========================================== */

  async function play(
    name,
  ) {

    if (!enabled) {
      return;
    }


    const context =
      await ensureReady();


    if (!context) {
      return;
    }


    switch (name) {


      /* -------------------------------------
         UI CLICK
      ------------------------------------- */

      case "click":

        tone({
          frequency: 700,
          endFrequency: 900,
          duration: 0.055,
          volume: 0.55,
          type: "square",
        });

        break;


      /* -------------------------------------
         CHALLENGE OPEN
      ------------------------------------- */

      case "challenge":

      case "challenge-open":

        tone({
          frequency: 280,
          endFrequency: 520,
          duration: 0.09,
          volume: 0.65,
          type: "triangle",
        });


        tone({
          frequency: 520,
          endFrequency: 820,
          duration: 0.12,
          volume: 0.5,
          type: "triangle",
          startTime: 0.07,
        });

        break;


      /* -------------------------------------
         CORRECT ANSWER
      ------------------------------------- */

      case "correct":

        tone({
          frequency: 620,
          duration: 0.08,
          volume: 0.55,
          type: "triangle",
        });


        tone({
          frequency: 830,
          duration: 0.09,
          volume: 0.55,
          type: "triangle",
          startTime: 0.07,
        });


        tone({
          frequency: 1040,
          duration: 0.14,
          volume: 0.6,
          type: "sine",
          startTime: 0.14,
        });

        break;


      /* -------------------------------------
         WRONG ANSWER
      ------------------------------------- */

      case "wrong":

        tone({
          frequency: 240,
          endFrequency: 180,
          duration: 0.15,
          volume: 0.55,
          type: "sawtooth",
        });


        tone({
          frequency: 170,
          endFrequency: 120,
          duration: 0.18,
          volume: 0.4,
          type: "sawtooth",
          startTime: 0.11,
        });

        break;


      /* -------------------------------------
         XP GAIN
      ------------------------------------- */

      case "xp":

  tone({
    frequency: 760,
    endFrequency: 980,
    duration: 0.08,
    volume: 0.70,
    type: "triangle",
  });

  tone({
    frequency: 980,
    endFrequency: 1320,
    duration: 0.14,
    volume: 0.75,
    type: "triangle",
    startTime: 0.07,
  });

  break;


      /* -------------------------------------
         LEVEL UP
      ------------------------------------- */

      case "levelup":

case "level-up":

  tone({
    frequency: 392,
    duration: 0.14,
    volume: 0.75,
    type: "triangle",
  });

  tone({
    frequency: 523,
    duration: 0.14,
    volume: 0.75,
    type: "triangle",
    startTime: 0.12,
  });

  tone({
    frequency: 659,
    duration: 0.14,
    volume: 0.80,
    type: "triangle",
    startTime: 0.24,
  });

  tone({
    frequency: 784,
    duration: 0.32,
    volume: 0.90,
    type: "sine",
    startTime: 0.36,
  });

  break;


      /* -------------------------------------
         ACHIEVEMENT
      ------------------------------------- */

      case "achievement":

  tone({
    frequency: 660,
    duration: 0.12,
    volume: 0.75,
    type: "triangle",
  });

  tone({
    frequency: 880,
    duration: 0.12,
    volume: 0.75,
    type: "triangle",
    startTime: 0.10,
  });

  tone({
    frequency: 1046,
    duration: 0.14,
    volume: 0.80,
    type: "triangle",
    startTime: 0.20,
  });

  tone({
    frequency: 1318,
    duration: 0.35,
    volume: 0.90,
    type: "sine",
    startTime: 0.32,
  });

  break;


      /* -------------------------------------
         NOTIFICATION
      ------------------------------------- */

      case "notification":

        tone({
          frequency: 560,
          duration: 0.08,
          volume: 0.35,
          type: "sine",
        });


        tone({
          frequency: 760,
          duration: 0.12,
          volume: 0.4,
          type: "sine",
          startTime: 0.09,
        });

        break;


      /* -------------------------------------
         UNKNOWN
      ------------------------------------- */

      default:

        console.warn(
          `[CyberRealm] Unknown sound: ${name}`,
        );

        break;
    }
  }


  /* =========================================
     PUBLIC API
  ========================================== */

  window.CyberSound = {
  play,
  enable() {
    enabled = true;
  },
  disable() {
    enabled = false;
  },
  toggle() {
    enabled = !enabled;
    return enabled;
  },
  isEnabled() {
    return enabled;
  },
  setVolume(volume) {
    masterVolume = Math.max(
      0,
      Math.min(1, Number(volume) || 0),
    );
  },
  getVolume() {
    return masterVolume;
  },
  async resume() {
    await ensureReady();
  },
};


  /* =========================================
     RESUME AUDIO AFTER USER INTERACTION
  ========================================== */

  const resumeAudio =
    () => {
      ensureReady();
    };


  document.addEventListener(
    "pointerdown",
    resumeAudio,
    {
      once: true,
      passive: true,
    },
  );


  document.addEventListener(
    "keydown",
    resumeAudio,
    {
      once: true,
      passive: true,
    },
  );

})();