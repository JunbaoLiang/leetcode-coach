// UI label dictionaries (PLAN §10 controlled vocabulary, §11.3 patterns).

export const PATTERN_LABELS: Record<string, string> = {
  primers: '入门热身',
  arrays_hashing: '数组/哈希',
  two_pointers: '双指针',
  sliding_window: '滑动窗口',
  binary_search: '二分查找',
  stack: '栈',
  linked_list: '链表',
  trees: '树',
  bfs: 'BFS',
  dfs: 'DFS',
  heap: '堆',
  backtracking: '回溯',
  graphs: '图',
  topological_sort: '拓扑排序',
  union_find: '并查集',
  dp_1d: '一维 DP',
  greedy: '贪心',
  intervals: '区间',
  math: '数学',
  sql: 'SQL',
}

export const MISTAKE_TAG_LABELS: Record<string, string> = {
  misread_problem: '读错/漏读题意',
  edge_case_missed: '边界条件遗漏',
  off_by_one: '差一错误',
  wrong_data_structure: '数据结构选型不当',
  pattern_not_recognized: '没识别出 pattern',
  complexity_misjudged: '复杂度估错/超时',
  recursion_base_case: '递归终止条件错误',
  dp_state_definition: 'DP 状态定义错误',
  implementation_bug: '思路对,代码手滑',
  numerical_stability: '数值稳定性问题',
  api_unfamiliar: '不熟语言内置工具',
}

export const OUTCOME_LABELS: Record<string, string> = {
  ac_first_try: '一次 AC',
  ac: 'AC(非一次)',
  failed: '未通过',
  abandoned: '放弃',
}

export const RECALL_LABELS = [
  '0 · 完全忘了',
  '1 · 几乎不记得',
  '2 · 模糊印象',
  '3 · 想起来但费劲',
  '4 · 较顺利',
  '5 · 毫不费力',
]

export const DIFFICULTY_LABELS: Record<string, string> = {
  easy: '简单',
  medium: '中等',
  hard: '困难',
}

export function patternLabel(p: string): string {
  return PATTERN_LABELS[p] ?? p
}
