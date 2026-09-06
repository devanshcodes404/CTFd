import Alpine from "alpinejs";
import CTFd from "../index";
import { colorHash } from "@ctfdio/ctfd-js/ui";
import { getOption as getUserScoreOption } from "../utils/graphs/echarts/userscore";
import { embed } from "../utils/graphs/echarts";

window.Alpine = Alpine;

Alpine.data("UserGraphs", () => ({
  solves: null,
  fails: null,
  awards: null,
  solveCount: 0,
  failCount: 0,
  awardCount: 0,

  getSolvePercentage() {
    return ((this.solveCount / (this.solveCount + this.failCount)) * 100).toFixed(2);
  },

  getFailPercentage() {
    return ((this.failCount / (this.solveCount + this.failCount)) * 100).toFixed(2);
  },

  getCategoryBreakdown() {
    const categories = [];
    const breakdown = {};

    this.solves.data.map(solve => {
      categories.push(solve.challenge.category);
    });

    categories.forEach(category => {
      if (category in breakdown) {
        breakdown[category] += 1;
      } else {
        breakdown[category] = 1;
      }
    });

    const data = [];
    for (const property in breakdown) {
      const percent = Number((breakdown[property] / categories.length) * 100).toFixed(
        2,
      );

      data.push({
        name: property,
        count: breakdown[property],
        color: colorHash(property),
        percent,
      });
    }

    return data;
  },

  async init() {
    this.solves = await CTFd.pages.users.userSolves("me");
    this.fails = await CTFd.pages.users.userFails("me");
    this.awards = await CTFd.pages.users.userAwards("me");

    this.solveCount = this.solves.meta.count;
    this.failCount = this.fails.meta.count;
    this.awardCount = this.awards.meta.count;

    let optionMerge = window.userScoreGraphChartOptions;

    embed(
      this.$refs.scoregraph,
      getUserScoreOption(
        CTFd.user.id,
        CTFd.user.name,
        this.solves.data,
        this.awards.data,
        optionMerge,
      ),
    );
  },
}));

Alpine.data("CyberRealmProfile", () => ({
  profile: {
    xp: 0,
    level: 1,
    rank: "RECRUIT",
    nextRank: "OPERATIVE",
nextRankLevel: 5,

    xpPerLevel: 500,
    xpIntoLevel: 0,
    xpToNext: 500,
    progress: 0,

    streak: 0,
    longestStreak: 0,
    totalSolves: 0,

    achievementsUnlocked: 0,
    achievementsTotal: 0,

    achievements: [],
  },

  async init() {
    if (!window.init || !window.init.userId) {
      console.log(
        "[CyberRealm] No logged-in user for profile.",
      );

      return;
    }

    try {
      const response = await fetch(
        `/api/v1/esecurityin/profile/${window.init.userId}`,
        {
          headers: {
            Accept: "application/json",
          },
        },
      );

      if (!response.ok) {
        throw new Error(
          `HTTP ${response.status}`,
        );
      }

      const data = await response.json();

      console.log(
        "[CyberRealm] Profile:",
        data,
      );

      this.updateProfile(data);

    } catch (error) {
      console.error(
        "[CyberRealm] Failed to fetch profile:",
        error,
      );
    }
  },

  updateProfile(data) {
    const progression =
      data.progression || {};

    const achievements =
      data.achievements || {};

    const XP_PER_LEVEL = 500;

    const xp =
      progression.xp || 0;

    const level =
      progression.level || 1;

    const xpIntoLevel =
      xp % XP_PER_LEVEL;

    const progress =
      Number(
        (
          xpIntoLevel /
          XP_PER_LEVEL
        ) * 100
      ).toFixed(1);

    const xpToNext =
      XP_PER_LEVEL -
      xpIntoLevel;

    const nextRank = this.getNextRank(level);

this.profile = {
  xp,
  level,

  rank: this.getPlayerRank(level),

  nextRank: nextRank.name,
  nextRankLevel: nextRank.level,

      xpPerLevel:
        XP_PER_LEVEL,

      xpIntoLevel,
      xpToNext,
      progress,

      streak:
        progression.streak || 0,

      longestStreak:
        progression.longest_streak || 0,

      totalSolves:
        progression.total_solves || 0,

      achievementsUnlocked:
        achievements.unlocked || 0,

      achievementsTotal:
        achievements.total || 0,

      achievements:
        achievements.items || [],
    };
  },

  getPlayerRank(level) {
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
},

getNextRank(level) {
  if (level >= 50) {
    return {
      name: "MAX RANK",
      level: 50,
    };
  }

  if (level >= 30) {
    return {
      name: "CYBER LEGEND",
      level: 50,
    };
  }

  if (level >= 20) {
    return {
      name: "SHADOW AGENT",
      level: 30,
    };
  }

  if (level >= 10) {
    return {
      name: "ELITE",
      level: 20,
    };
  }

  if (level >= 5) {
    return {
      name: "SPECIALIST",
      level: 10,
    };
  }

  return {
    name: "OPERATIVE",
    level: 5,
  };
},
}));
Alpine.data("CyberRealmStats", () => ({
  stats: {
  solves: 0,
  fails: 0,
  solveRate: "0.00",
  totalAttempts: 0,
  longestStreak: 0,
  categories: [],
},
  async init() {
    if (!window.init || !window.init.userId) {
      console.log(
        "[CyberRealm] No logged-in user for stats.",
      );

      return;
    }

    try {
      const solvesResponse = await fetch(
        `/api/v1/users/me/solves`,
        {
          headers: {
            Accept: "application/json",
          },
        },
      );

      const failsResponse = await fetch(
        `/api/v1/users/me/fails`,
        {
          headers: {
            Accept: "application/json",
          },
        },
      );

      if (
        !solvesResponse.ok ||
        !failsResponse.ok
      ) {
        throw new Error(
          "Unable to load solve statistics",
        );
      }

      const solvesData =
        await solvesResponse.json();

      const failsData =
        await failsResponse.json();

      const solves =
        solvesData.data || [];

      const fails =
        failsData.data || [];

      const solveCount =
        solves.length;

      const failCount =
        fails.length;

      const totalAttempts =
        solveCount + failCount;

      const solveRate =
        totalAttempts > 0
          ? (
              (solveCount / totalAttempts) *
              100
            ).toFixed(2)
          : "0.00";

      const categories = {};

      for (const solve of solves) {

        const category =
          solve.challenge?.category ||
          "Unknown";

        if (!categories[category]) {
          categories[category] = 0;
        }

        categories[category]++;
      }

      const categoryTotal =
        solveCount || 1;

      const categoryData =
        Object.entries(categories)
          .map(([name, count]) => ({
            name,
            count,
            percent:
              (
                (count / categoryTotal) *
                100
              ).toFixed(1),
          }))
          .sort(
            (a, b) =>
              b.count - a.count,
          );

      const profileResponse =
        await fetch(
          `/api/v1/esecurityin/profile/${window.init.userId}`,
          {
            headers: {
              Accept:
                "application/json",
            },
          },
        );

      let longestStreak = 0;

      if (profileResponse.ok) {
        const profileData =
          await profileResponse.json();

        longestStreak =
          profileData.progression
            ?.longest_streak || 0;
      }

      this.stats = {
  solves: solveCount,
  fails: failCount,
  solveRate,
  totalAttempts,
  longestStreak,
  categories: categoryData,
};

    } catch (error) {
      console.error(
        "[CyberRealm] Failed to load progression statistics:",
        error,
      );
    }
  },
}));
Alpine.start();
