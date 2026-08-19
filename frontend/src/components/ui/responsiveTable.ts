/**
 * Class names that turn a table into a list of cards on small screens.
 *
 * The admin lists are genuinely tabular on a laptop, and a table is the right
 * markup for them: screen readers announce the column a value belongs to, and
 * the header row does real work. On a phone the same markup is unreadable --
 * five columns in 375 pixels either clip or force sideways scrolling, and both
 * mean the owner cannot check attendance from the car.
 *
 * Rather than render the data twice, one for each layout, the table elements
 * switch their display: below `sm` every row becomes a card and every cell a
 * line within it, and the header is hidden because a card carries its own
 * labels. Above `sm` it is an ordinary table again.
 *
 * Cells that need a label on mobile carry `data-label`, which is drawn from
 * the attribute by CSS. Duplicating the markup instead would mean two places
 * to update every time a column changes, and they would drift.
 *
 * Usage:
 *
 *   <table className={table.root}>
 *     <thead className={table.head}> ... </thead>
 *     <tbody className={table.body}>
 *       <tr className={table.row}>
 *         <td className={table.cellPrimary}>Name</td>
 *         <td className={table.cell} data-label="Grade">11</td>
 */
export const table = {
  root: "w-full text-left text-sm",

  // Column headers mean nothing once each row is a card.
  head: "hidden border-b border-ink-200 bg-ink-50 sm:table-header-group",

  body: "block divide-y divide-ink-200 sm:table-row-group",

  // A card on mobile: padding and a visible edge. A plain row above sm.
  row: "block px-4 py-3.5 transition-colors hover:bg-ink-50 sm:table-row sm:px-0 sm:py-0",

  // The name or title. Stays prominent and needs no label.
  cellPrimary: "block pb-1 sm:table-cell sm:px-5 sm:py-4",

  // A labelled line inside the card; an ordinary cell above sm.
  cell: [
    "flex items-baseline justify-between gap-3 py-0.5 text-ink-700",
    "before:text-xs before:font-medium before:uppercase before:tracking-wide",
    "before:text-ink-400 before:content-[attr(data-label)]",
    "sm:table-cell sm:px-5 sm:py-4 sm:before:content-none",
  ].join(" "),

  // Right-aligned numbers, which should stay right-aligned as a table.
  cellNumeric: [
    "flex items-baseline justify-between gap-3 py-0.5 tabular-nums text-ink-700",
    "before:text-xs before:font-medium before:uppercase before:tracking-wide",
    "before:text-ink-400 before:content-[attr(data-label)]",
    "sm:table-cell sm:px-5 sm:py-4 sm:text-right sm:before:content-none",
  ].join(" "),

  // Actions sit under the card on mobile, at the end of the row on desktop.
  cellAction:
    "mt-2 flex justify-end border-t border-ink-100 pt-2 sm:mt-0 sm:table-cell sm:border-0 sm:px-5 sm:py-4 sm:pt-4 sm:text-right",

  // Wrapper: never overflow-hidden, which clips a wide table on a phone
  // instead of letting it scroll.
  wrapper:
    "mt-8 overflow-x-auto rounded-xl border border-ink-200 bg-white shadow-[var(--shadow-card)]",
} as const;
