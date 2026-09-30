/** Placeholder for shadcn-compatible class helpers when components are introduced. */
export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}
