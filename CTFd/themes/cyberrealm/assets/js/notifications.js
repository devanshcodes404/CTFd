import Alpine from "alpinejs";
import CTFd from "@ctfdio/ctfd-js";

window.Alpine = Alpine;
window.CTFd = CTFd;


/* =========================================
   CYBERREALM NOTIFICATION STORE
========================================= */

const NotificationStore = {

  notifications: [],

  loading: false,

  initialized: false,

  pollingStarted: false,

  initialLoadComplete: false,


  /* =========================================
     LOAD NOTIFICATIONS
  ========================================== */

  async load({
    announce = false,
  } = {}) {

    if (this.loading) {
      return;
    }

    this.loading = true;


    try {

      const response =
        await CTFd.fetch(
          "/api/v1/notifications"
        );


      if (!response.ok) {

        throw new Error(
          `Notifications HTTP ${response.status}`
        );

      }


      const result =
        await response.json();


      const incoming =
        (result.data || [])
          .sort(
            (a, b) =>
              new Date(b.date) -
              new Date(a.date)
          );


      /*
       * Detect notifications that did not
       * exist during the previous load.
       */

      if (
        announce &&
        this.initialLoadComplete
      ) {

        const existingIds =
          new Set(
            this.notifications.map(
              notification =>
                notification.id
            )
          );


        const newNotifications =
          incoming.filter(
            notification =>
              !existingIds.has(
                notification.id
              )
          );


        newNotifications
          .reverse()
          .forEach(
            notification =>
              this.announce(
                notification
              )
          );

      }


      this.notifications =
        incoming;


      this.syncUnreadCount();


      console.log(
        "[CyberRealm] Notifications loaded:",
        this.notifications
      );


      this.initialLoadComplete =
        true;

    } catch (error) {

      console.error(
        "[CyberRealm] Failed to load notifications:",
        error
      );

    } finally {

      this.loading = false;

    }

  },


  /* =========================================
     NOTIFICATION ANNOUNCEMENT
  ========================================== */

  announce(notification) {

    const title =
      String(
        notification.title || ""
      );


    const content =
      String(
        notification.content || ""
      );


    const lowerTitle =
      title.toLowerCase();


    /*
     * Achievement
     */

    if (
      lowerTitle.includes(
        "achievement"
      )
    ) {

      if (
        window.CyberSound
      ) {

        CyberSound.play(
          "achievement"
        );

      }


      if (
        window.Toast
      ) {

        Toast.success(
          `<strong>🏆 Achievement Unlocked</strong><br>${content}`
        );

      }

      return;

    }


    /*
     * Level up
     */

    if (
      lowerTitle.includes(
        "level"
      )
    ) {

      if (
        window.CyberSound
      ) {

        CyberSound.play(
          "levelup"
        );

      }


      if (
        window.Toast
      ) {

        Toast.success(
          `<strong>👑 Level Up</strong><br>${content}`
        );

      }

      return;

    }


    /*
     * Objective
     */

    if (
      lowerTitle.includes(
        "objective"
      )
    ) {

      if (
        window.CyberSound
      ) {

        CyberSound.play(
          "notification"
        );

      }


      if (
        window.Toast
      ) {

        Toast.info(
          `<strong>🎯 Objective Complete</strong><br>${content}`
        );

      }

      return;

    }


    /*
     * XP
     */

    if (
      lowerTitle.includes(
        "xp"
      )
    ) {

      if (
        window.CyberSound
      ) {

        CyberSound.play(
          "xp"
        );

      }


      if (
        window.Toast
      ) {

        Toast.success(
          `<strong>⚡ XP Gained</strong><br>${content}`
        );

      }

      return;

    }


    /*
     * Generic notification
     */

    if (
      window.CyberSound
    ) {

      CyberSound.play(
        "notification"
      );

    }


    if (
      window.Toast
    ) {

      Toast.info(
        `<strong>${title}</strong><br>${content}`
      );

    }

  },


  /* =========================================
     UNREAD COUNT
  ========================================== */

  syncUnreadCount() {

    if (
      !CTFd.events ||
      !CTFd.events.counter ||
      !CTFd.events.counter.read
    ) {

      return;

    }


    const readIds =
      new Set(
        CTFd.events.counter.read
          .getAll()
      );


    const unreadCount =
      this.notifications.filter(
        notification =>
          !readIds.has(
            notification.id
          )
      ).length;


    Alpine.store(
      "unread_count",
      unreadCount
    );

  },


  /* =========================================
     GET UNREAD
  ========================================== */

  getUnread() {

    if (
      !CTFd.events ||
      !CTFd.events.counter ||
      !CTFd.events.counter.read
    ) {

      return [];
    }


    const readIds =
      new Set(
        CTFd.events.counter.read
          .getAll()
      );


    return this.notifications.filter(
      notification =>
        !readIds.has(
          notification.id
        )
    );

  },


  /* =========================================
     MARK ONE READ
  ========================================== */

  markAsRead(
    notificationId
  ) {

    if (
      !CTFd.events ||
      !CTFd.events.counter
    ) {

      return;

    }


    const read =
      CTFd.events.counter.read
        .getAll();


    if (
      !read.includes(
        notificationId
      )
    ) {

      read.push(
        notificationId
      );

      CTFd.events.counter.read
        .setAll(
          read
        );

    }


    if (
      CTFd.events.counter.unread
    ) {

      CTFd.events.counter.unread
        .read(
          notificationId
        );

    }


    this.syncUnreadCount();

  },


  /* =========================================
     MARK ALL READ
  ========================================== */

  markAllAsRead() {

    if (
      !CTFd.events ||
      !CTFd.events.counter
    ) {

      return;

    }


    const unread =
      this.getUnread();


    const read =
      CTFd.events.counter.read
        .getAll();


    unread.forEach(
      notification => {

        if (
          !read.includes(
            notification.id
          )
        ) {

          read.push(
            notification.id
          );

        }


        if (
          CTFd.events.counter.unread
        ) {

          CTFd.events.counter.unread
            .read(
              notification.id
            );

        }

      }
    );


    CTFd.events.counter.read
      .setAll(
        read
      );


    this.syncUnreadCount();

  },


  /* =========================================
     POLLING
  ========================================== */

  startPolling() {

    if (
      this.pollingStarted
    ) {

      return;

    }


    this.pollingStarted =
      true;


    setInterval(
      () => {

        this.load({
          announce: true,
        });

      },
      10000
    );

  },


};


/* =========================================
   ALPINE COMPONENT
========================================= */

Alpine.data(
  "CyberRealmNotifications",
  () => ({

    notifications: [],

    loading: true,


    async init() {

      if (
        NotificationStore.initialized
      ) {

        this.sync();

        return;

      }


      NotificationStore.initialized =
        true;


      await NotificationStore.load({
        announce: false,
      });


      this.sync();


      NotificationStore.startPolling();

    },


    async refresh() {

      await NotificationStore.load({
        announce: false,
      });


      this.sync();

    },


    sync() {

      this.notifications =
        [
          ...NotificationStore.notifications
        ];


      this.loading =
        NotificationStore.loading;

    },


    get unread() {

      return NotificationStore
        .getUnread();

    },


    get unreadCount() {

      return this.unread.length;

    },


    markAsRead(id) {

      NotificationStore
        .markAsRead(id);

      this.sync();

    },


    markAllAsRead() {

      NotificationStore
        .markAllAsRead();

      this.sync();

    },


    formatDate(date) {

      if (!date) {
        return "";
      }


      const value =
        new Date(date);


      if (
        Number.isNaN(
          value.getTime()
        )
      ) {

        return "";
      }


      return value.toLocaleString();

    },


    icon(notification) {

      const title =
        String(
          notification.title || ""
        ).toLowerCase();


      if (
        title.includes(
          "achievement"
        )
      ) {

        return "🏆";

      }


      if (
        title.includes(
          "level"
        )
      ) {

        return "👑";

      }


      if (
        title.includes(
          "objective"
        )
      ) {

        return "🎯";

      }


      if (
        title.includes(
          "xp"
        )
      ) {

        return "⚡";

      }


      return "🔔";

    }

  })
);