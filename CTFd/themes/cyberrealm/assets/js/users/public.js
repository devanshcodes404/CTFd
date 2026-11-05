import CTFd from "../index";

import Alpine from "alpinejs";
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
    this.solves = await CTFd.pages.users.userSolves(window.USER.id);
    this.fails = await CTFd.pages.users.userFails(window.USER.id);
    this.awards = await CTFd.pages.users.userAwards(window.USER.id);

    this.solveCount = this.solves.meta.count;
    this.failCount = this.fails.meta.count;
    this.awardCount = this.awards.meta.count;

    let optionMerge = window.userScoreGraphChartOptions;

    embed(
      this.$refs.scoregraph,
      getUserScoreOption(
        window.USER.id,
        window.USER.name,
        this.solves.data,
        this.awards.data,
        optionMerge,
      ),
    );
  },
}));


import firstBreachImage from "../../img/brooches/first-breach.png";
import breachRunnerImage from "../../img/brooches/breach-runner.png";
import eliteOperatorImage from "../../img/brooches/elite-operator.png";
import cryptoSpecialistImage from "../../img/brooches/crypto-specialist.png";
import webDefenderImage from "../../img/brooches/web-defender.png";
import xpHunterImage from "../../img/brooches/xp-hunter.png";
import missionCommanderImage from "../../img/brooches/mission-commander.png";
import stageMasterImage from "../../img/brooches/stage-master.png";

const BROOCH_ASSETS = {
  first_breach: firstBreachImage,
  breach_runner: breachRunnerImage,
  elite_operator: eliteOperatorImage,
  crypto_specialist: cryptoSpecialistImage,
  web_defender: webDefenderImage,
  xp_hunter: xpHunterImage,
  mission_commander: missionCommanderImage,
  stage_master: stageMasterImage,
};

Alpine.data("PublicProfileAwards", () => ({
  loading: true,
  achievements: [],
  brooches: [],
  achievementsCount: 0,
  broochesCount: 0,
  totalAwardsCount: 0,

  async init() {
    if (!window.USER || !window.USER.id) {
      this.loading = false;
      return;
    }
    try {
      const res = await fetch(`/api/v1/esecurityin/profile/${window.USER.id}/public-awards`);
      if (res.ok) {
        const data = await res.json();
        const ach = data.achievements || {};
        const bro = data.brooches || {};
        this.achievements = ach.items || [];
        this.achievementsCount = ach.unlocked || this.achievements.length;
        this.brooches = (bro.items || []).map(b => {
          const asset = BROOCH_ASSETS[b.asset_key];
          return {
            ...b,
            assetUrl: asset ? `/themes/cyberrealm/static${asset}` : null,
          };
        });
        this.broochesCount = bro.unlocked || this.brooches.length;
        this.totalAwardsCount = this.achievementsCount + this.broochesCount;
      }
    } catch (err) {
      console.error("[CyberRealm] Failed to load public awards:", err);
    } finally {
      this.loading = false;
    }
  },
}));

Alpine.start();
