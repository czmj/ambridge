import { formatDate } from '../../../lib/utils';
import { getCharacterProfile, getCharacterTimeline } from '../../actions';
import Timeline from '@/components/Timeline';

export default async function CharacterProfile({ params, searchParams }) {
  const resolvedParams = await params;
  const resolvedSearch = await searchParams;
  const slug = resolvedParams.slug;
  const currentPage = parseInt(resolvedSearch.page) || 1;
  const pageSize = 10;

  const profile = await getCharacterProfile(slug);
  const { episodes, totalCount } = await getCharacterTimeline(slug, currentPage, pageSize);

  if (!profile) return <div>Character not found</div>;

  const { details } = profile;

  return (
    <div className="max-w-4xl mx-auto p-6">
      <header className="my-12 border-b border-gray-200 pb-2">
        <h1 className="text-4xl mb-2">What happened with <span className="font-bold">{details.name}</span>?</h1>
        <p className="text-gray-400 text-sm tracking-widest uppercase">
          {details.dob ? `Born: ${formatDate(details.dob)}` : 'DOB Unknown'} 
          {details.dod ? ` - Died: ${formatDate(details.dod)}` : ''}
        </p>
      </header>
      
      <Timeline 
        episodes={episodes} 
        totalCount={totalCount} 
        currentPage={currentPage}
        baseUrl={`/character/${slug}`}
        pageSize={pageSize}
      />
    </div>
  );
}