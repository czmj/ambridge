import Link from 'next/link';

export default function SortOrder({ baseUrl, currentSort = 'desc' }: {
  baseUrl: string,
  currentSort: 'asc' | 'desc'
}) {
  const options = [
    { id: 'desc', label: 'Newest First' },
    { id: 'asc', label: 'Oldest First' }
  ];

  return (
    <nav
      className="mb-4 flex gap-3 text-sm text-gray-600"
      aria-label="Sort order"
    >
      {options.map((option, index) => (
        <span key={option.id} className="flex items-center gap-3">
          {currentSort === option.id ? (
            <span
              className="text-blue-600"
              aria-current="true"
            >
              {option.label}
            </span>
          ) : (
            <Link
              href={`${baseUrl}?sort=${option.id}`}
              className="hover:text-blue-600 transition-colors"
            >
              {option.label}
            </Link>
          )}

          {index < options.length - 1 && (
            <span aria-hidden="true" className="text-gray-400">|</span>
          )}
        </span>
      ))}
    </nav>
  );
}