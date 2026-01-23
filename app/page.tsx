import Timeline from '@/components/Timeline';
import { Subtitle } from '@/components/Typography';
import { getTimeline } from './actions';

type HomePageProps = {
  searchParams: {
    sort?: 'asc' | 'desc'
    page?: string
  }
}

export default async function Home({ searchParams }: HomePageProps) {
  const resolvedSearch = await searchParams;
  const page = resolvedSearch.page ? parseInt(resolvedSearch.page) : 1;
  const pageSize = 10;
  const sort = resolvedSearch.sort;

  const { episodes, totalCount } = await getTimeline({ page, pageSize, sort });

  return (
    <>
      <header className="my-12 border-b border-gray-200 pb-2">
        <h1 className="text-4xl mb-2">What happened in Ambridge?</h1>
        <Subtitle>
          A chronological history
        </Subtitle>
      </header>

      <Timeline
        episodes={episodes}
        totalCount={totalCount}
        currentPage={page}
        pageSize={pageSize}
        baseUrl="/"
        sort={sort}
      />
    </>
  );
}