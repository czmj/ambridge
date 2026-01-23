import Link from 'next/link';
import { getTimeline } from './actions';
import Timeline from '@/components/Timeline';

export default async function Home({ searchParams }) {
  const resolvedSearch = await searchParams;
  const currentPage = parseInt(resolvedSearch.page) || 1;
  const pageSize = 10;

  // Fetch the global data
  const { episodes, totalCount } = await getTimeline(currentPage, pageSize);

  return (
    <div className="max-w-5xl mx-auto p-6">
      <header className="my-12 border-b border-gray-200 pb-2">
        <h1 className="text-4xl mb-2">What happened in Ambridge?</h1>
        <p className="text-gray-400 text-sm tracking-widest uppercase">
          A chronological history
        </p>
      </header>

      <Timeline 
        episodes={episodes} 
        totalCount={totalCount} 
        currentPage={currentPage}
        pageSize={pageSize}
        baseUrl="/"
      />
    </div>
  );
}