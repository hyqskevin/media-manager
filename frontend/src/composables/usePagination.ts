/** 通用分页 composable：把大数据列表切成当前页的可见子集。

使用：
```ts
const { page, size, pagedRows, total } = usePagination(rows)
```
其中 `pagedRows` 是基于当前页/页大小切片后的响应式数组。
*/
import { computed, ref } from 'vue'

export type UsePaginationOptions = {
  defaultPage?: number
  defaultSize?: number
  /** 可选的页大小选项；默认 [10, 20, 50, 100] */
  sizeOptions?: number[]
}

export function usePagination<T>(
  rowsGetter: () => readonly T[],
  options: UsePaginationOptions = {},
) {
  const page = ref(options.defaultPage ?? 1)
  const size = ref(options.defaultSize ?? 20)
  const sizeOptions = options.sizeOptions ?? [10, 20, 50, 100]

  const total = computed(() => rowsGetter().length)
  const pagedRows = computed(() => {
    const all = rowsGetter()
    const start = (page.value - 1) * size.value
    const end = start + size.value
    return all.slice(start, end)
  })

  /** 切页或改 size 时调用，确保 page 不超出范围 */
  function ensureValidPage() {
    if (page.value < 1) page.value = 1
    const max = Math.max(1, Math.ceil(total.value / size.value))
    if (page.value > max) page.value = max
  }

  function onSizeChange(newSize: number) {
    size.value = newSize
    page.value = 1
  }

  function onPageChange(newPage: number) {
    page.value = newPage
  }

  return { page, size, sizeOptions, total, pagedRows, ensureValidPage, onSizeChange, onPageChange }
}