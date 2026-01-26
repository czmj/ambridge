export function Subtitle({ children, className = "", as: Component = "p" }) {
  const baseClasses = "text-sm text-gray-600 italic";

  return (
    <Component className={`${baseClasses} ${className}`}>
      {children}
    </Component>
  );
}