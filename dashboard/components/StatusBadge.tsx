type Status = "emerging" | "maturing" | "saturating";

const config: Record<Status, { label: string; className: string }> = {
  emerging:   { label: "Emerging",   className: "bg-green-100 text-green-800" },
  maturing:   { label: "Maturing",   className: "bg-yellow-100 text-yellow-800" },
  saturating: { label: "Saturating", className: "bg-red-100 text-red-800" },
};

export function StatusBadge({ status }: { status: string }) {
  const s = (status as Status) in config ? (status as Status) : "emerging";
  const { label, className } = config[s];
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${className}`}>
      {label}
    </span>
  );
}
