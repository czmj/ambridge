import Link from 'next/link';
import { slugify } from '../lib/utils';

export default function CharacterList({ characters = [] }) {

  return (
    <div className="flex flex-wrap gap-2 items-center mt-4">
      {characters.map(c => {
        const slug = slugify(c)
        return (
          <Link 
            key={slug}
            href={`/character/${slug}`}
            className="px-2 py-1 bg-blue-50 text-blue-700 text-sm rounded-full border border-blue-200 hover:bg-blue-600 hover:text-white transition-colors"
          >
            {c}
          </Link>
        )}
      )}
    </div>
  );
}