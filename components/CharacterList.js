import Link from 'next/link';
import { slugify } from '../lib/utils';

import { useId } from 'react'

export default function CharacterList({ characters = [] }) {
  return (
    <div className="flex flex-wrap gap-2 items-center mt-4">
      {characters.map(c => {
        const key = useId();

        return (
          <Link 
            key={key}
            href={`/character/${c.slug}`}
            className="px-2 py-1 bg-blue-50 text-blue-700 text-sm rounded-full border border-blue-200 hover:bg-blue-600 hover:text-white transition-colors"
          >
            {c.name}
          </Link>
        )}
      )}
    </div>
  );
}