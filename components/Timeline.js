import Link from 'next/link';
import CharacterList from './CharacterList';

export default function Timeline({ episodes, totalCount, currentPage, slug, pageSize }) {
  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div className="mt-8 pl-3">
      {!!episodes.length && (
        <div className="space-y-16 border-l-4 border-blue-500">
          {episodes.map((ep) => {

            return (
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
                <h2 className="text-2xl font-bold mb-4">
                  {ep.date}
                </h2>

                <div className="space-y-10">
                  {ep.scenes.map((scene) => (
                    <div key={scene.sceneId}>
                      <div className="scene-text text-gray-900 leading-relaxed">
                        {scene.text}
                      </div>

                      {scene.others.length > 0 && (
                        <div className="mt-4">
                          <CharacterList characters={scene.others} />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="mt-20 py-10 border-t border-gray-200 flex justify-between items-center text-sm tracking-widest uppercase">
        {currentPage > 1 ? (
          <Link href={`/character/${slug}?page=${currentPage - 1}`} className="hover:underline">
            ← Newer
          </Link>
        ) : <div />}

        {totalPages ? (<span className="text-gray-400">Page {currentPage} / {totalPages}</span>) : <p>No appearances in archive</p>}


        {totalPages && currentPage < totalPages ? (
          <Link href={`/character/${slug}?page=${currentPage + 1}`} className="hover:underline">
            Older →
          </Link>
        ) : <div />}
      </div>
    </div>
  );
}