import { useEffect, useId, useMemo, useRef, useState } from "react";
import { Check, ChevronDown, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

const ROW_HEIGHT = 36;
const MAX_HEIGHT = 280;
const OVERSCAN = 4;

export default function SearchableCombobox({
  label,
  value,
  onChange,
  options = [],
  placeholder = "Type to search...",
  loading = false,
  disabled = false,
}) {
  const id = useId();
  const rootRef = useRef(null);
  const listRef = useRef(null);
  const inputRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState(value || "");
  const [activeIndex, setActiveIndex] = useState(0);
  const [scrollTop, setScrollTop] = useState(0);

  useEffect(() => setQuery(value || ""), [value]);

  const filtered = useMemo(() => {
    const text = query.trim().toLowerCase();
    if (!text) return options;
    return options.filter((option) => option.label.toLowerCase().includes(text));
  }, [options, query]);

  const selectedIndex = filtered.findIndex((option) => option.value === value);
  const totalHeight = filtered.length * ROW_HEIGHT;
  const visibleCount = Math.ceil(MAX_HEIGHT / ROW_HEIGHT) + OVERSCAN;
  const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
  const visibleItems = filtered.slice(startIndex, startIndex + visibleCount);

  useEffect(() => {
    const close = (event) => {
      if (!rootRef.current?.contains(event.target)) setOpen(false);
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, []);

  useEffect(() => {
    if (!open) return;
    const index = Math.max(0, selectedIndex);
    setActiveIndex(index);
    requestAnimationFrame(() => {
      listRef.current?.scrollTo({ top: Math.max(0, index * ROW_HEIGHT - ROW_HEIGHT * 2), behavior: "smooth" });
    });
  }, [open, selectedIndex]);

  const commit = (option) => {
    if (!option) return;
    onChange(option.value);
    setQuery(option.label);
    setOpen(false);
    inputRef.current?.blur();
  };

  const onKeyDown = (event) => {
    if (disabled) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setOpen(true);
      setActiveIndex((index) => {
        const next = Math.min(filtered.length - 1, index + 1);
        listRef.current?.scrollTo({ top: Math.max(0, next * ROW_HEIGHT - ROW_HEIGHT * 5), behavior: "smooth" });
        return next;
      });
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setOpen(true);
      setActiveIndex((index) => {
        const next = Math.max(0, index - 1);
        listRef.current?.scrollTo({ top: Math.max(0, next * ROW_HEIGHT - ROW_HEIGHT * 2), behavior: "smooth" });
        return next;
      });
    } else if (event.key === "Enter") {
      if (open && filtered[activeIndex]) {
        event.preventDefault();
        commit(filtered[activeIndex]);
      }
    } else if (event.key === "Escape") {
      setOpen(false);
      setQuery(value || "");
    }
  };

  const status = loading ? "Loading..." : !query && !filtered.length ? "Type to search..." : !filtered.length ? "No results found" : null;

  return (
    <div ref={rootRef} className="relative min-w-0">
      {label ? <label htmlFor={id} className="text-sm font-medium leading-none">{label}</label> : null}
      <div className="relative mt-1.5">
        <input
          ref={inputRef}
          id={id}
          role="combobox"
          aria-expanded={open}
          aria-controls={`${id}-listbox`}
          aria-autocomplete="list"
          aria-activedescendant={open && filtered[activeIndex] ? `${id}-option-${activeIndex}` : undefined}
          disabled={disabled}
          value={query}
          placeholder={placeholder}
          onFocus={() => setOpen(true)}
          onClick={() => setOpen(true)}
          onChange={(event) => {
            setQuery(event.target.value);
            onChange(event.target.value);
            setOpen(true);
            setActiveIndex(0);
            listRef.current?.scrollTo({ top: 0 });
          }}
          onKeyDown={onKeyDown}
          className="flex h-9 w-full rounded-md border border-input bg-transparent py-1 pl-3 pr-9 text-base shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 md:text-sm"
        />
        <button
          type="button"
          tabIndex={-1}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground"
          onClick={() => {
            if (!disabled) {
              setOpen((current) => !current);
              inputRef.current?.focus();
            }
          }}
          aria-label={`Toggle ${label || "options"}`}
        >
          {loading ? <Loader2 size={16} className="animate-spin" /> : <ChevronDown size={16} />}
        </button>
      </div>

      {open ? (
        <div className="absolute z-50 mt-1 w-full max-w-[min(100vw-2rem,100%)] overflow-hidden rounded-md border border-border bg-popover text-popover-foreground shadow-lg">
          <div
            ref={listRef}
            id={`${id}-listbox`}
            role="listbox"
            className="aq-scrollbar max-h-[280px] overflow-y-auto overflow-x-hidden scroll-smooth p-1"
            style={{ height: filtered.length ? Math.min(MAX_HEIGHT, totalHeight + 8) : 72 }}
            onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
          >
            {status ? (
              <div className="grid h-16 place-items-center px-3 text-sm text-muted-foreground">{status}</div>
            ) : (
              <div style={{ height: totalHeight, position: "relative" }}>
                {visibleItems.map((option, offset) => {
                  const index = startIndex + offset;
                  const selected = option.value === value;
                  const active = index === activeIndex;
                  return (
                    <button
                      key={`${option.value}-${index}`}
                      id={`${id}-option-${index}`}
                      type="button"
                      role="option"
                      aria-selected={selected}
                      className={cn(
                        "absolute left-0 right-0 flex h-9 w-full items-center justify-between rounded-sm px-2 text-left text-sm outline-none transition-colors",
                        active || selected ? "bg-accent text-accent-foreground" : "hover:bg-accent/70"
                      )}
                      style={{ top: index * ROW_HEIGHT }}
                      onMouseEnter={() => setActiveIndex(index)}
                      onClick={() => commit(option)}
                    >
                      <span className="truncate">{option.label}</span>
                      {selected ? <Check size={15} className="shrink-0 text-primary" /> : null}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
