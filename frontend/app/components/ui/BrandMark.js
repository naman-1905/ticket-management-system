export default function BrandMark({ size = "md" }) {
  const sizes = {
    sm: "text-base",
    md: "text-xl",
    lg: "text-2xl",
  };

  return (
    <span className={`font-semibold tracking-tight text-foreground ${sizes[size]}`}>
      <span className="text-accent">T</span>ickets
    </span>
  );
}
