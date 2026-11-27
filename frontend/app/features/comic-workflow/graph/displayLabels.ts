import type { ComicWorkflowNodeKind } from "./types";

export const NODE_KIND_LABELS: Record<ComicWorkflowNodeKind, string> = {
	brief: "故事简介",
	character: "角色",
	shot: "分镜",
	output: "最终成片",
};

const STYLE_LABELS: Record<string, string> = {
	anime: "日漫", shonen: "少年热血", "slice-of-life": "日常治愈",
	manga: "黑白漫画", donghua: "国风动画", cinematic: "电影质感",
	pixar: "3D 卡通", lowpoly: "低多边形", watercolor: "水彩",
	sketch: "素描", realistic: "写实",
};

export function styleLabel(style: string | null | undefined): string {
	return style ? STYLE_LABELS[style] ?? style : "未设置";
}
