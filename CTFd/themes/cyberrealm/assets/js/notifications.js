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

  errors: {
    list: "",
    count: "",
    mutation: "",
  },

  async retry() {
    if (this.failedMutation?.type === "one") {
      return this.markAsRead(this.failedMutation.id);
    }
    if (this.failedMutation?.type === "all") {
      return this.markAllAsRead();
    }
    return this.reload();
  },

  unreadCount: 0,

  markingIds: new Set(),

  markingAll: false,

  failedMutation: null,

  subscribers: new Set(),

  initialized: false,

  pollingStarted: false,

  initialLoadComplete: false,

  loadPromise: null,


  /* =========================================
     LOAD NOTIFICATIONS
  ========================================== */

  async load({
    announce = false,
  } = {}) {
    if (this.loadPromise) {
      return this.loadPromise;
    }

    this.loadPromise = this.loadNotifications({ announce });

    try {
      return await this.loadPromise;
    } finally {
      this.loadPromise = null;
    }
  },

  async loadNotifications({ announce }) {
    if (this.loading) {
      return false;
    }

    this.loading = true;
    this.notifySubscribers();

    try {
      const [listResult, countResult] = await Promise.allSettled([
        this.fetchJson("/api/v1/notifications"),
        this.fetchUnreadCount(),
      ]);

      const listLoaded = listResult.status === "fulfilled";
      const countLoaded = countResult.status === "fulfilled";

      if (listLoaded) {
        const incoming = (listResult.value.data || [])
          .map(notification => ({
            ...notification,
            read: Boolean(notification.read),
          }))
          .sort(
            (a, b) =>
              new Date(b.date) - new Date(a.date)
          );

        if (announce && this.initialLoadComplete) {
          const existingIds = new Set(
            this.notifications.map(notification => notification.id)
          );
          incoming
            .filter(notification => !existingIds.has(notification.id))
            .reverse()
            .forEach(notification => this.announce(notification));
        }

        this.notifications = incoming;
        this.errors.list = "";
        this.initialLoadComplete = true;
        console.log(
          "[CyberRealm] Notifications loaded:",
          this.notifications
        );
      } else {
        this.errors.list = `GET /api/v1/notifications failed: ${this.errorMessage(
          listResult.reason
        )}`;
        console.error(
          "[CyberRealm] Failed to load notifications:",
          listResult.reason
        );
      }

      if (countLoaded) {
        this.unreadCount = countResult.value;
        this.errors.count = "";
        this.syncUnreadCount();
      } else {
        this.errors.count = `HEAD /api/v1/notifications unread count failed: ${this.errorMessage(
          countResult.reason
        )}`;
        console.error(
          "[CyberRealm] Failed to refresh unread notification count:",
          countResult.reason
        );
      }

      this.notifySubscribers();
      return listLoaded && countLoaded;
    } finally {
      this.loading = false;
      this.notifySubscribers();
    }
  },

  async reload() {
    if (this.loadPromise) {
      await this.loadPromise;
    }
    return this.load({ announce: false });
  },

  async fetchJson(url, options = {}) {
    const response = await CTFd.fetch(url, options);
    let result;

    try {
      result = await response.json();
    } catch {
      throw new Error(`Notifications request failed (${response.status})`);
    }

    if (!response.ok || result.success === false) {
      const detail =
        result.errors?.[0]?.message ||
        result.message ||
        response.statusText;
      throw new Error(
        detail
          ? `Notifications request failed (${response.status}): ${detail}`
          : `Notifications request failed (${response.status})`
      );
    }

    return result;
  },

  async fetchUnreadCount() {
    const response = await CTFd.fetch(
      "/api/v1/notifications",
      { method: "HEAD" }
    );

    if (!response.ok) {
      const detail = response.statusText;
      throw new Error(
        detail
          ? `Unread count request failed (${response.status}): ${detail}`
          : `Unread count request failed (${response.status})`
      );
    }

    const unreadCount = response.headers.get("Unread-Count");
    if (!unreadCount || !/^\d+$/.test(unreadCount)) {
      throw new Error(
        "Unread count response was missing a valid Unread-Count header"
      );
    }

    const count = Number(unreadCount);
    if (!Number.isSafeInteger(count)) {
      throw new Error(
        "Unread count response contained an invalid Unread-Count header"
      );
    }

    return count;
  },

  errorMessage(error) {
    return error instanceof Error ? error.message : String(error);
  },

  getErrorMessage() {
    return Object.values(this.errors).filter(Boolean).join(" ");
  },

  notifySubscribers() {
    this.subscribers.forEach(
      subscriber => subscriber()
    );
  },

  subscribe(subscriber) {
    this.subscribers.add(subscriber);
    return () => this.subscribers.delete(subscriber);
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
    Alpine.store(
      "unread_count",
      this.unreadCount
    );
  },


  /* =========================================
     GET UNREAD
  ========================================== */

  getUnread() {
    return this.notifications.filter(
      notification => !notification.read
    );
  },


  /* =========================================
     MARK ONE READ
  ========================================== */

  async markAsRead(notificationId) {
    const id = String(notificationId);
    const notification = this.notifications.find(
      item => String(item.id) === id
    );

    if (
      !notification ||
      notification.read ||
      this.markingIds.has(id) ||
      this.markingAll
    ) {
      return false;
    }

    this.failedMutation = null;
    this.markingIds.add(id);
    this.notifySubscribers();

    try {
      await this.fetchJson(
        `/api/v1/notifications/${encodeURIComponent(id)}/read`,
        { method: "POST", body: JSON.stringify({}) }
      );

      notification.read = true;
      this.errors.mutation = "";
      this.failedMutation = null;
      await this.refreshUnreadCount();
      return true;
    } catch (error) {
      this.failedMutation = { type: "one", id };
      this.errors.mutation = `POST /api/v1/notifications/${id}/read failed: ${this.errorMessage(
        error
      )}. Retry the action.`;
      console.error(
        "[CyberRealm] Failed to mark notification as read:",
        error
      );
      return false;
    } finally {
      this.markingIds.delete(id);
      this.notifySubscribers();
    }
  },


  /* =========================================
     MARK ALL READ
  ========================================== */

  async markAllAsRead() {
    if (this.markingAll || this.markingIds.size > 0) {
      return false;
    }

    if (this.getUnread().length === 0 && this.unreadCount === 0) {
      this.failedMutation = null;
      this.errors.mutation = "";
      return true;
    }

    this.failedMutation = null;
    this.markingAll = true;
    this.notifySubscribers();

    try {
      await this.fetchJson(
        "/api/v1/notifications/read",
        { method: "POST", body: JSON.stringify({}) }
      );

      this.errors.mutation = "";
      this.failedMutation = null;
      if (!await this.reload()) {
        console.error(
          "[CyberRealm] Notifications were marked as read, but the refresh was incomplete."
        );
      }
      return true;
    } catch (error) {
      this.failedMutation = { type: "all" };
      this.errors.mutation = `POST /api/v1/notifications/read failed: ${this.errorMessage(
        error
      )}. Retry the action.`;
      console.error(
        "[CyberRealm] Failed to mark all notifications as read:",
        error
      );
      return false;
    } finally {
      this.markingAll = false;
      this.notifySubscribers();
    }
  },

  async refreshUnreadCount() {
    try {
      this.unreadCount = await this.fetchUnreadCount();
      this.errors.count = "";
      this.syncUnreadCount();
      return true;
    } catch (error) {
      this.errors.count = `HEAD /api/v1/notifications unread count failed: ${this.errorMessage(
        error
      )}`;
      console.error(
        "[CyberRealm] Failed to refresh unread notification count:",
        error
      );
      return false;
    } finally {
      this.notifySubscribers();
    }
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
    listLoaded: false,
    error: "",
    markingIds: new Set(),
    markingAll: false,
    unsubscribe: null,
    async init() {
      this.unsubscribe =
        NotificationStore.subscribe(() => this.sync());
      if (!NotificationStore.initialized) {
        NotificationStore.initialized = true;
        await NotificationStore.load({ announce: false });
      } else {
        this.sync();
      }
      NotificationStore.startPolling();
    },
    async refresh() {
      await NotificationStore.load({ announce: false });
    },
    async retry() {
      return NotificationStore.retry();
    },
    destroy() {
      if (this.unsubscribe) {
        this.unsubscribe();
        this.unsubscribe = null;
      }
    },
    sync() {
      this.notifications = NotificationStore.notifications.map(
        notification => ({ ...notification })
      );
      this.loading = NotificationStore.loading;
      this.listLoaded = NotificationStore.initialLoadComplete;
      this.error = NotificationStore.getErrorMessage();
      this.markingIds = new Set(NotificationStore.markingIds);
      this.markingAll = NotificationStore.markingAll;
    },
    get unreadCount() {
      return NotificationStore.unreadCount;
    },
    get hasUnread() {
      return (
        this.unreadCount > 0 ||
        this.notifications.some(notification => !notification.read)
      );
    },
    isMarking(id) {
      return this.markingIds.has(String(id));
    },
    async markAsRead(id) {
      await NotificationStore.markAsRead(id);
    },
    async markAllAsRead() {
      await NotificationStore.markAllAsRead();
    },
    formatDate(date) {
      if (!date) {
        return "";
      }
      const value = new Date(date);
      if (Number.isNaN(value.getTime())) {
        return "";
      }
      return value.toLocaleString();
    },
    icon(notification) {
      const title = String(notification.title || "").toLowerCase();
      if (title.includes("achievement")) {
        return "🏆";
      }
      if (title.includes("level")) {
        return "👑";
      }
      if (title.includes("objective")) {
        return "🎯";
      }
      if (title.includes("xp")) {
        return "⚡";
      }
      return "🔔";
    },
  })
);