"use client";

import { useRef, useEffect } from "react";
import * as f3 from "family-chart";
import { useRouter } from "next/navigation";

export type FamilyDatum = f3.Datum & {
  data: {
    gender: "M" | "F";
    name: string;
    dob?: string;
    dod?: string;
    partnerStatuses?: Record<string, string>;
  };
};

type FamilyTreeProps = {
  data: FamilyDatum[];
  focusSlug: string;
};

export default function FamilyTree({ data, focusSlug }: FamilyTreeProps) {
  const container = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    if (!container.current) return;

    const f3Chart = f3
      .createChart(container.current, data)
      .setTransitionTime(0)
      .setShowSiblingsOfMain(true)
      .setSortChildrenFunction((a, b) => a.data.dob - b.data.dob)
      .setSortSpousesFunction((d) => {
        d.rels.spouses.sort((a, b) => {
          const aCurrent = d.data.partnerStatuses?.[a] === "current" ? 0 : 1;
          const bCurrent = d.data.partnerStatuses?.[b] === "current" ? 0 : 1;
          return aCurrent - bCurrent;
        });
      })
      .setSingleParentEmptyCard(false);

    f3Chart
      .setCardHtml()
      .setStyle("rect")
      .setCardDim({
        w: 150,
      })
      .setCardDisplay(
        [
        "name",
        (d: FamilyDatum) => {
          if (d.data.dob) {
            return d.data.dod
              ? [`${d.data.dob} - ${d.data.dod}`]
              : [`b. ${d.data.dob}`];
          }

          if (d.data.dod) {
            return [`d. ${d.data.dod}`];
          }

          return "";
        },
      ])
      .setOnCardClick((event: MouseEvent, data: f3.TreeDatum) => {
        router.push(`/to/${data.tid}`)
      });

    f3Chart.updateTree({ initial: true }).updateMainId(focusSlug);

  }, [data, focusSlug, router]);

  return (
    <div className="family-tree-wrapper">
      <div
        className="f3"
        ref={container}
        style={{ width: "100%", height: "600px" }}
      ></div>
    </div>
  );
}
