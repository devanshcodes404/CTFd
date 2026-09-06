import { cumulativeSum } from "../../math";
import { mergeObjects } from "../../objects";
import dayjs from "dayjs";

export function getOption(id, name, solves, awards, optionMerge) {
  let option = {
    backgroundColor: "transparent",

    title: {
      left: "center",
      top: 0,
      text: "Score Over Time",
      textStyle: {
        color: "#94a3b8",
        fontSize: 12,
        fontWeight: 700,
      },
    },

    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(8, 14, 24, 0.96)",
      borderColor: "rgba(0, 255, 200, 0.25)",
      borderWidth: 1,
      textStyle: {
        color: "#f5f7fa",
        fontSize: 11,
      },
      axisPointer: {
        type: "cross",
        crossStyle: {
          color: "#00ffc8",
        },
        lineStyle: {
          color: "rgba(0, 255, 200, 0.3)",
        },
      },
    },

    legend: {
      type: "scroll",
      orient: "horizontal",
      align: "left",
      bottom: 0,
      data: [name],
      textStyle: {
        color: "#94a3b8",
        fontSize: 9,
      },
    },

    toolbox: {
      right: 10,
      top: 0,
      iconStyle: {
        borderColor: "#64748b",
      },
      feature: {
        saveAsImage: {
          backgroundColor: "#080b14",
        },
      },
    },

    grid: {
      top: 45,
      right: 20,
      bottom: 55,
      left: 45,
      containLabel: true,
    },

    xAxis: [
      {
        type: "category",
        boundaryGap: false,
        data: [],
        axisLine: {
          lineStyle: {
            color: "#26364c",
          },
        },
        axisTick: {
          lineStyle: {
            color: "#26364c",
          },
        },
        axisLabel: {
          color: "#64748b",
          fontSize: 9,
        },
        splitLine: {
          show: false,
        },
      },
    ],

    yAxis: [
      {
        type: "value",
        axisLine: {
          lineStyle: {
            color: "#26364c",
          },
        },
        axisTick: {
          lineStyle: {
            color: "#26364c",
          },
        },
        axisLabel: {
          color: "#64748b",
          fontSize: 9,
        },
        splitLine: {
          lineStyle: {
            color: "rgba(148, 163, 184, 0.08)",
          },
        },
      },
    ],

    dataZoom: [
      {
        id: "dataZoomX",
        type: "slider",
        xAxisIndex: [0],
        filterMode: "filter",
        height: 16,
        top: 32,
        borderColor: "rgba(0, 255, 200, 0.08)",
        backgroundColor: "rgba(255, 255, 255, 0.03)",
        fillerColor: "rgba(0, 255, 200, 0.10)",
        handleStyle: {
          color: "#00ffc8",
          borderColor: "#00ffc8",
        },
        moveHandleStyle: {
          color: "#00aaff",
        },
        textStyle: {
          color: "#64748b",
          fontSize: 8,
        },
      },
    ],

    series: [],
  };

  const times = [];
  const scores = [];
  const total = solves.concat(awards);

  total.sort((a, b) => {
    return new Date(a.date) - new Date(b.date);
  });

  for (let i = 0; i < total.length; i++) {
    const date = dayjs(total[i].date);

    times.push(date.toDate());

    try {
      scores.push(total[i].challenge.value);
    } catch (e) {
      scores.push(total[i].value);
    }
  }

  times.forEach(time => {
    option.xAxis[0].data.push(time);
  });

  option.series.push({
    name: name,
    type: "line",
    smooth: true,
    showSymbol: true,
    symbol: "circle",
    symbolSize: 6,

    label: {
  show: false,
},

    lineStyle: {
      color: "#00ffc8",
      width: 2,
      shadowColor: "rgba(0, 255, 200, 0.35)",
      shadowBlur: 8,
    },

    itemStyle: {
      color: "#00ffc8",
      borderColor: "#080b14",
      borderWidth: 2,
      shadowColor: "rgba(0, 255, 200, 0.45)",
      shadowBlur: 8,
    },

    areaStyle: {
      color: {
        type: "linear",
        x: 0,
        y: 0,
        x2: 0,
        y2: 1,
        colorStops: [
          {
            offset: 0,
            color: "rgba(0, 255, 200, 0.20)",
          },
          {
            offset: 1,
            color: "rgba(0, 170, 255, 0.02)",
          },
        ],
      },
    },

    emphasis: {
      focus: "series",
      itemStyle: {
        color: "#00ffc8",
        borderColor: "#ffffff",
        borderWidth: 2,
        shadowColor: "rgba(0, 255, 200, 0.7)",
        shadowBlur: 12,
      },
    },

    data: cumulativeSum(scores),
  });

  if (optionMerge) {
    option = mergeObjects(option, optionMerge);
  }

  return option;
}