import CharacterList from './CharacterList';

type ScenesListProps = {
    scenes: any[], // TODO
}

export default function ScenesList({ scenes }: ScenesListProps) {
    return (
        <div className="space-y-6">
            {scenes.map((scene) => (
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
    );
}