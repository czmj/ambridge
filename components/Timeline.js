import Link from 'next/link';
import CharacterList from './CharacterList';
import { formatDate } from '@/lib/utils';

export default function Timeline({ episodes, totalCount, currentPage, baseUrl, pageSize, sort = 'desc' }) {
  const totalPages = Math.ceil(totalCount / pageSize);
  const today = new Date();
  const thirtyDaysInMs = 30 * 24 * 60 * 60 * 1000;

  const isAvailableToListen = (episodeDate) => {
    const epDate = new Date(`${episodeDate} 19:15`);
    return today - epDate <= thirtyDaysInMs;
  };

  return (
    <div>
      {!!episodes.length && (
        <>
          <div className="mb-3 flex gap-3 text-sm text-gray-500">
            <Link
              href={`${baseUrl}?sort=desc`}
              className={`hover:text-blue-600 ${sort === 'desc' ? 'font-bold text-blue-600' : ''}`}
            >
              Newest First
            </Link>
            |
            <Link
              href={`${baseUrl}?sort=asc`}
              className={`hover:text-blue-600 ${sort === 'asc' ? 'font-bold text-blue-600' : ''}`}
            >
              Oldest First
            </Link>
          </div>
          <div className="space-y-16 border-l-4 border-blue-500 ml-3">
            {episodes.map((ep) => (
              <div key={ep.episodePid} className="
                pl-8
                relative 
                before:content-[''] 
                before:block 
                before:box-border 
                before:w-8 
                before:h-8 
                before:border-4 
                before:border-solid 
                before:border-blue-500
                before:rounded-full 
                before:absolute 
                before:-left-4.5 
                before:bg-white
              ">
                <header className="mb-4">
                  <h2 className="text-2xl font-bold">
                    {formatDate(ep.date, {
                      weekday: "long",
                      day: 'numeric',
                      month: 'long',
                      year: 'numeric',
                    })}
                  </h2>
                  {isAvailableToListen(ep.date) && (
                    <div>
                      <a
                        href={`https://www.bbc.co.uk/programmes/${ep.episodePid}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline text-sm font-medium"
                      >
                        Listen again on BBC Sounds
                      </a>
                    </div>)}
                </header>

                <div className="space-y-6">
                  {ep.scenes.map((scene) => (
                    <div key={scene.sceneId}>
                      <div className="scene-text text-gray-900 leading-relaxed">
                        {scene.text}
                      </div>

                      {scene.characters?.length > 0 && (
                        <div className="mt-4">
                          <CharacterList characters={scene.characters} />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )
            )}
          </div>
        </>
      )}

      <div className="mt-20 py-10 border-t border-gray-200 flex justify-between items-center text-sm tracking-widest uppercase">
        {currentPage > 1 ? (
          <Link href={`${baseUrl}?page=${currentPage - 1}&sort=${sort}`} className="hover:underline">
            ← {sort === 'desc' ? 'Newer' : 'Older'}
          </Link>
        ) : <div />}

        {totalPages ? (<span className="text-gray-400">Page {currentPage} / {totalPages}</span>) : <p>No appearances</p>}

        {totalPages && currentPage < totalPages ? (
          <Link href={`${baseUrl}?page=${currentPage + 1}&sort=${sort}`} className="hover:underline">
            {sort === 'desc' ? 'Older' : 'Newer'} →
          </Link>
        ) : <div />}
      </div>
    </div>
  );
}