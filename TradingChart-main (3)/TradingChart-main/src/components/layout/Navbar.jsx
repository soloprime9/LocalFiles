'use client'
import { useState } from 'react';
import { NavLink, Link } from 'react-router-dom';
import { BarChart3, Menu, X, Search } from 'lucide-react';
import SearchBar from '../ui/SearchBar';
import { useAppContext } from '../../context/AppContext';

const NAV_LINKS = [
  { label: 'Trending', emoji: '🔥', to: '/trending' },
  { label: 'New', emoji: '⚡', to: '/new' },
  { label: 'Top Rated', emoji: '⭐', to: '/top-rated' },
  { label: 'Free', emoji: '🆓', to: '/free' },
  { label: 'Categories', to: '/categories' },
  { label: 'Strategies', to: '/strategies' },
  { label: 'AI Finder', to: '/ai-finder', highlight: true },
  { label: 'Brokers', to: '/brokers' },
];

function NavItem({ link, onClick, mobile = false }) {
  return (
    <NavLink
      to={link.to}
      onClick={onClick}
      className={({ isActive }) =>
        [
          mobile
            ? 'flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium'
            : 'relative flex items-center gap-1 px-1 py-1 text-sm font-medium',
          link.highlight
            ? 'bg-amber-500 text-black rounded-full px-3'
            : isActive
            ? 'text-white'
            : 'text-gray-400 hover:text-white transition-colors',
          mobile && isActive && !link.highlight ? 'bg-[#1A1A1A]' : '',
        ].join(' ')
      }
    >
      {({ isActive }) => (
        <>
          {link.emoji && <span aria-hidden>{link.emoji}</span>}
          {link.label}
          {!mobile && !link.highlight && isActive && (
            <span className="absolute -bottom-2 left-0 right-0 h-0.5 bg-amber-500 rounded-full" />
          )}
        </>
      )}
    </NavLink>
  );
}

export default function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [mobileSearchOpen, setMobileSearchOpen] = useState(false);
  const { compareList } = useAppContext();

  return (
    <header className="sticky top-0 z-50 bg-[#0A0A0A] border-b border-[#1F2937] overflow-x-hidden">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-16 gap-4">
          <Link to="/" className="flex items-center gap-2 shrink-0">
            <BarChart3 className="w-6 h-6 text-amber-500" />
            <span className="text-white font-bold text-lg">
              FalconSpido<span className="text-amber-500">.</span>
            </span>
          </Link>

          <nav className="hidden xl:flex items-center gap-5 flex-1 min-w-0">
            {NAV_LINKS.map((link) => (
              <NavItem key={link.to} link={link} />
            ))}
          </nav>

          <div className="hidden xl:block w-64 shrink-0">
            <SearchBar />
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => setMobileSearchOpen((o) => !o)}
              className="xl:hidden p-2 text-gray-400 hover:text-white"
              aria-label="Search"
            >
              <Search className="w-5 h-5" />
            </button>

            <Link
              to="/compare"
              className="hidden sm:flex items-center gap-1.5 text-sm font-medium text-gray-300 hover:text-white border border-[#1F2937] hover:border-[#374151] rounded-lg px-3 py-1.5 transition-colors"
            >
              Compare
              {compareList.length > 0 && (
                <span className="bg-amber-500 text-black text-xs font-semibold rounded-full px-1.5 py-0.5 min-w-[18px] text-center">
                  {compareList.length}
                </span>
              )}
            </Link>

            <Link
              to="/submit"
              className="hidden sm:inline-flex bg-amber-500 text-black text-sm font-semibold rounded-lg px-4 py-2 hover:bg-amber-400 transition-colors whitespace-nowrap"
            >
              Submit Indicator
            </Link>

            <button
              type="button"
              onClick={() => setMobileOpen((o) => !o)}
              className="xl:hidden p-2 text-gray-300"
              aria-label="Menu"
            >
              {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {mobileSearchOpen && (
          <div className="xl:hidden pb-3">
            <SearchBar autoFocus />
          </div>
        )}
      </div>

      {mobileOpen && (
        <div className="xl:hidden border-t border-[#1F2937] bg-[#0A0A0A] px-4 py-3">
          <nav className="flex flex-col gap-1">
            {NAV_LINKS.map((link) => (
              <NavItem key={link.to} link={link} mobile onClick={() => setMobileOpen(false)} />
            ))}
            <div className="border-t border-[#1F2937] mt-2 pt-3 flex flex-col gap-2">
              <Link
                to="/compare"
                onClick={() => setMobileOpen(false)}
                className="flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium text-gray-300 hover:bg-[#1A1A1A]"
              >
                Compare
                {compareList.length > 0 && (
                  <span className="bg-amber-500 text-black text-xs font-semibold rounded-full px-1.5 py-0.5">
                    {compareList.length}
                  </span>
                )}
              </Link>
              <Link
                to="/submit"
                onClick={() => setMobileOpen(false)}
                className="bg-amber-500 text-black text-sm font-semibold rounded-lg px-3 py-2.5 text-center"
              >
                Submit Indicator
              </Link>
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}









// 'use client'
// import { useState } from 'react';
// import { NavLink, Link } from 'react-router-dom';
// import { BarChart3, Menu, X, Search } from 'lucide-react';
// import SearchBar from '../ui/SearchBar';
// import { useAppContext } from '../../context/AppContext';

// const NAV_LINKS = [
//   { label: 'Trending', emoji: '🔥', to: '/trending' },
//   { label: 'New', emoji: '⚡', to: '/new' },
//   { label: 'Top Rated', emoji: '⭐', to: '/top-rated' },
//   { label: 'Free', emoji: '🆓', to: '/free' },
//   { label: 'Categories', to: '/categories' },
//   { label: 'Strategies', to: '/strategies' },
//   { label: 'AI Finder', to: '/ai-finder', highlight: true },
//   { label: 'Brokers', to: '/brokers' },
// ];

// function NavItem({ link, onClick, mobile = false }) {
//   return (
//     <NavLink
//       to={link.to}
//       onClick={onClick}
//       className={({ isActive }) =>
//         [
//           mobile
//             ? 'flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium'
//             : 'relative flex items-center gap-1 px-1 py-1 text-sm font-medium',
//           link.highlight
//             ? 'bg-amber-500 text-black rounded-full px-3'
//             : isActive
//             ? 'text-white'
//             : 'text-gray-400 hover:text-white transition-colors',
//           mobile && isActive && !link.highlight ? 'bg-[#1A1A1A]' : '',
//         ].join(' ')
//       }
//     >
//       {({ isActive }) => (
//         <>
//           {link.emoji && <span aria-hidden>{link.emoji}</span>}
//           {link.label}
//           {!mobile && !link.highlight && isActive && (
//             <span className="absolute -bottom-2 left-0 right-0 h-0.5 bg-amber-500 rounded-full" />
//           )}
//         </>
//       )}
//     </NavLink>
//   );
// }

// export default function Navbar() {
//   const [mobileOpen, setMobileOpen] = useState(false);
//   const [mobileSearchOpen, setMobileSearchOpen] = useState(false);
//   const { compareList } = useAppContext();

//   return (
//     <header className="sticky top-0 z-50 bg-[#0A0A0A] border-b border-[#1F2937]">
//       <div className="max-w-7xl mx-auto px-4">
//         <div className="flex items-center justify-between h-16 gap-4">
//           <Link to="/" className="flex items-center gap-2 shrink-0">
//             <BarChart3 className="w-6 h-6 text-amber-500" />
//             <span className="text-white font-bold text-lg">
//               IndicatorHub<span className="text-amber-500">.</span>
//             </span>
//           </Link>

//           <nav className="hidden lg:flex items-center gap-5 flex-1">
//             {NAV_LINKS.map((link) => (
//               <NavItem key={link.to} link={link} />
//             ))}
//           </nav>

//           <div className="hidden lg:block w-64 shrink-0">
//             <SearchBar />
//           </div>

//           <div className="flex items-center gap-2 shrink-0">
//             <button
//               type="button"
//               onClick={() => setMobileSearchOpen((o) => !o)}
//               className="lg:hidden p-2 text-gray-400 hover:text-white"
//               aria-label="Search"
//             >
//               <Search className="w-5 h-5" />
//             </button>

//             <Link
//               to="/compare"
//               className="hidden sm:flex items-center gap-1.5 text-sm font-medium text-gray-300 hover:text-white border border-[#1F2937] hover:border-[#374151] rounded-lg px-3 py-1.5 transition-colors"
//             >
//               Compare
//               {compareList.length > 0 && (
//                 <span className="bg-amber-500 text-black text-xs font-semibold rounded-full px-1.5 py-0.5 min-w-[18px] text-center">
//                   {compareList.length}
//                 </span>
//               )}
//             </Link>

//             <Link
//               to="/submit"
//               className="hidden sm:inline-flex bg-amber-500 text-black text-sm font-semibold rounded-lg px-4 py-2 hover:bg-amber-400 transition-colors whitespace-nowrap"
//             >
//               Submit Indicator
//             </Link>

//             <button
//               type="button"
//               onClick={() => setMobileOpen((o) => !o)}
//               className="lg:hidden p-2 text-gray-300"
//               aria-label="Menu"
//             >
//               {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
//             </button>
//           </div>
//         </div>

//         {mobileSearchOpen && (
//           <div className="lg:hidden pb-3">
//             <SearchBar autoFocus />
//           </div>
//         )}
//       </div>

//       {mobileOpen && (
//         <div className="lg:hidden border-t border-[#1F2937] bg-[#0A0A0A] px-4 py-3">
//           <nav className="flex flex-col gap-1">
//             {NAV_LINKS.map((link) => (
//               <NavItem key={link.to} link={link} mobile onClick={() => setMobileOpen(false)} />
//             ))}
//             <div className="border-t border-[#1F2937] mt-2 pt-3 flex flex-col gap-2">
//               <Link
//                 to="/compare"
//                 onClick={() => setMobileOpen(false)}
//                 className="flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium text-gray-300 hover:bg-[#1A1A1A]"
//               >
//                 Compare
//                 {compareList.length > 0 && (
//                   <span className="bg-amber-500 text-black text-xs font-semibold rounded-full px-1.5 py-0.5">
//                     {compareList.length}
//                   </span>
//                 )}
//               </Link>
//               <Link
//                 to="/submit"
//                 onClick={() => setMobileOpen(false)}
//                 className="bg-amber-500 text-black text-sm font-semibold rounded-lg px-3 py-2.5 text-center"
//               >
//                 Submit Indicator
//               </Link>
//             </div>
//           </nav>
//         </div>
//       )}
//     </header>
//   );
// }
