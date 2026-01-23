import { ExternalLink } from 'lucide-react';

export default function ListenAgain({pid}: {pid: string}) {
    if (!pid) return null;

    return (
        <a
            href={`https://www.bbc.co.uk/programmes/${pid}`}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-blue-600 inline-flex gap-1 items-center"
        >
            Listen again on BBC Sounds <ExternalLink size={14} aria-label="(Opens in new tab)" />
        </a>
    );
}