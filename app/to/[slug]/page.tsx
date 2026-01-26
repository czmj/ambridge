import Timeline from '@/components/Timeline';
import { Subtitle } from '@/components/Typography';
import { formatDate } from '@/lib/utils';
import { notFound } from 'next/navigation';
import { getCharacterProfile, getTimeline } from '../../actions';

type CharacterPageProps = {
  params: {
    slug: string
  },
  searchParams: {
    sort?: 'asc' | 'desc'
    page?: string
  }
}

export default async function CharacterPage({ params, searchParams }: CharacterPageProps) {
  const resolvedParams = await params;
  const resolvedSearch = await searchParams;
  const slug = resolvedParams.slug;
  const sort = resolvedSearch.sort;
  const page = resolvedSearch.page ? parseInt(resolvedSearch.page) : 1;
  const pageSize = 10;

  const profile = await getCharacterProfile(slug);
  const { episodes, totalCount } = await getTimeline({ page, pageSize, sort, slug });

  if (!profile) {
    notFound();
  }

  const { name, dob, dod } = profile;

  return (
    <>
      <header className="mt-12 mb-6 border-b border-gray-200 pb-2">
        <h1 className="text-4xl mb-2">What happened to <span className="font-bold">{name}</span>?</h1>
        <Subtitle>
          {dob ? `Born: ${formatDate(dob)}` : 'Date of Birth Unknown'}
          {dod ? ` - Died: ${formatDate(dod)}` : ''}
        </Subtitle>
      </header>

      <Timeline
        episodes={episodes}
        totalCount={totalCount}
        currentPage={page}
        baseUrl={`/to/${slug}`}
        pageSize={pageSize}
        sort={sort}
      />
    </>
  );
}