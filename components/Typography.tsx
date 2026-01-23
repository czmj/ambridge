export function Subtitle({ children, className = "", as: Component = "p" }) {
  const baseClasses = "text-sm text-gray-600 tracking-widest uppercase";

  return (
    <Component className={`${baseClasses} ${className}`}>
      {children}
    </Component>
  );
}