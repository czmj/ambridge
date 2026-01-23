import { ExternalLink } from 'lucide-react';

export default function ListenAgain({pid, date}: {pid: string, date?: string}) {
    if (!pid) return null;

    const today = new Date().getTime();
    const thirtyDaysInMs = 30 * 24 * 60 * 60 * 1000;
    const airDate = new Date(`${date} 19:15`).getTime();

    return (
        <a
            href={`https://www.bbc.co.uk/programmes/${pid}`}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-blue-600 inline-flex gap-1 items-center"
        >
            {date && today - airDate <= thirtyDaysInMs ? 'Listen again' : 'Archived'} on BBC Sounds <ExternalLink size={14} aria-label="(Opens in new tab)" />
        </a>
    );
}