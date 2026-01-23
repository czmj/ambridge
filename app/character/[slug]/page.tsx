import Timeline from '@/components/Timeline';
import { Subtitle } from '@/components/Typography';
import { formatDate } from '../../../lib/utils';
import { getCharacterProfile, getTimeline } from '../../actions';

type CharacterPageProps = {
  params: {
    slug: string
  },
  searchParams: {
    sort?: string
    page?: string
  }
}

export default async function CharacterPage({ params, searchParams }: CharacterPageProps) {
  const resolvedParams = await params;
  const resolvedSearch = await searchParams;
  const slug = resolvedParams.slug;
  const sort = resolvedSearch.sort;
  const currentPage = resolvedSearch.page ? parseInt(resolvedSearch.page) : 1;
  const pageSize = 10;

  const profile = await getCharacterProfile(slug);
  const { episodes, totalCount } = await getTimeline(currentPage, pageSize, sort, slug);

  if (!profile) return <div>Character not found</div>;

  const { details } = profile;

  return (
    <>
      <header className="my-12 border-b border-gray-200 pb-2">
        <h1 className="text-4xl mb-2">What happened with <span className="font-bold">{details.name}</span>?</h1>
        <Subtitle>
          {details.dob ? `Born: ${formatDate(details.dob)}` : 'Date of Birth Unknown'}
          {details.dod ? ` - Died: ${formatDate(details.dod)}` : ''}
        </Subtitle>
      </header>

      <Timeline
        episodes={episodes}
        totalCount={totalCount}
        currentPage={currentPage}
        baseUrl={`/character/${slug}`}
        pageSize={pageSize}
        sort={sort}
      />
    </>
  );
}