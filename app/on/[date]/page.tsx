import { getEpisodeByDate } from '@/app/actions';
import ScenesList from '@/components/ScenesList';
import { Subtitle } from '@/components/Typography';
import { notFound } from 'next/navigation';
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

export default async function DatePage({ params }: DatePageProps) {
  const resolvedParams = await params;
  const date = resolvedParams.date;
  const episode = await getEpisodeByDate(date);

  if (!episode) {
    notFound();
  }

  return (
    <>
      <header className="mt-12 mb-6 border-b border-gray-200 pb-2">
        <h1 className="text-4xl mb-2">What happened on <span className="font-bold">{formatDate(date)}</span>?</h1>
        <Subtitle>{episode.synopsis}</Subtitle>
      </header>
      <ScenesList scenes={episode.scenes} />
    </>
  );
}