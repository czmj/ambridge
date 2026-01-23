import { formatDate } from '@/lib/utils';
import { MoveLeft, MoveRight } from 'lucide-react';
import Link from 'next/link';
import CharacterList from './CharacterList';
import ListenAgain from './ListenAgain';
import SortOrder from './SortOrder';
import { Subtitle } from './Typography';

type TimelineProps = {
  episodes: any[], // TODO
  totalCount: number,
  currentPage: number,
  baseUrl: string,
  pageSize: number,
  sort?: 'asc' | 'desc'
}

export default function Timeline({ episodes, totalCount, currentPage, baseUrl, pageSize, sort = 'desc' }: TimelineProps) {
  const totalPages = Math.ceil(totalCount / pageSize);
  const today = new Date().getTime();
  const thirtyDaysInMs = 30 * 24 * 60 * 60 * 1000;

  const isAvailableToListen = (episodeDate: string) => {
    const epDate = new Date(`${episodeDate} 19:15`).getTime();
    return today - epDate <= thirtyDaysInMs;
  };

  return (
    <div>
      {!!episodes.length && (
        <>
          <SortOrder baseUrl={baseUrl} currentSort={sort} />
          <div className="space-y-16 border-l-4 border-blue-500 ml-3">
            {episodes.map((ep) => (
              <div key={ep.pid} className="
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
                  <p className="text-gray-500 text-sm inline-flex gap-2">
                    <Link
                      href={`/on/${ep.date}`}
                      className="hover:text-blue-600 transition-colors"
                    >
                      View episode
                    </Link>
                    {isAvailableToListen(ep.date) && (
                      <>
                        <span aria-hidden="true" className="text-gray-300">|</span>
                        <span>
                          <ListenAgain pid={ep.pid} />
                        </span>
                      </>)}
                  </p>
                </header>

                <div className="space-y-6">
                  {ep.scenes.map((scene) => (
                    <div key={scene.sceneId}>
                      <div className="text-gray-900 leading-relaxed">
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

      <Subtitle className="mt-20 py-10 border-t border-gray-200 flex justify-between items-center" as='div'>
        {currentPage > 1 ? (
          <Link href={`${baseUrl}?page=${currentPage - 1}&sort=${sort}`} className="hover:text-blue-600 text-gray-900 transition-colors flex items-center gap-1">
            <MoveLeft size={12} /> {sort === 'desc' ? 'Newer' : 'Older'}
          </Link>
        ) : <div />}

        {totalPages ? (<span>Page {currentPage} / {totalPages}</span>) : <p>No appearances</p>}

        {totalPages && currentPage < totalPages ? (
          <Link href={`${baseUrl}?page=${currentPage + 1}&sort=${sort}`} className="hover:text-blue-600 text-gray-900 transition-colors flex items-center gap-1">
            {sort === 'desc' ? 'Older' : 'Newer'} <MoveRight size={12} />
          </Link>
        ) : <div />}
      </Subtitle>
    </div>
  );
}