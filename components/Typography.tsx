export function Subtitle({ children, className = "", as: Component = "p" }) {
  const baseClasses = "text-sm text-gray-400 text-sm tracking-widest uppercase";

  return (
    <Component className={`${baseClasses} ${className}`}>
      {children}
    </Component>
  );
}