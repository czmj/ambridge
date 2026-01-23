import { Subtitle } from '@/components/Typography';
import { formatDate } from '../../../lib/utils';

type DatePageProps = {
  params: {
    date: string
  },
  searchParams: {
    sort?: 'asc' | 'desc'
    page?: string
  }
}

export default async function DatePage({ params, searchParams }: DatePageProps) {
  const resolvedParams = await params;
  const resolvedSearch = await searchParams;
  const date = resolvedParams.date;
  const page = resolvedSearch.page ? parseInt(resolvedSearch.page) : 1;
  const pageSize = 10;

  return (
    <>
      <header className="my-12 border-b border-gray-200 pb-2">
        <h1 className="text-4xl mb-2">What happened on <span className="font-bold">{formatDate(date)}</span>?</h1>
        <Subtitle>
          Some text here...
        </Subtitle>
      </header>
    </>
  );
}