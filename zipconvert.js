import React, { useState, useRef } from 'react';
import JSZip from 'jszip';
import { saveAs } from 'file-saver';
import { FolderUp, FileCheck, FileX, Archive, RefreshCw, Layers } from 'lucide-react';

export default function ZipExporter() {
  const [files, setFiles] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [compressionProgress, setCompressionProgress] = useState(0);
  const [downloadReady, setDownloadReady] = useState(false);
  const [zipBlob, setZipBlob] = useState(null);
  
  // Custom Ignore Settings (Default filters common tags)
  const [ignoredInput, setIgnoredInput] = useState('node_modules, .git, dist, build, .env');
  
  const fileInputRef = useRef(null);

  // Convert comma separated string to analytical clean array list
  const getIgnoredList = () => {
    return ignoredInput
      .split(',')
      .map(item => item.trim())
      .filter(item => item.length > 0);
  };

  // Handle direct recursive native folder imports from user's system layout 
  const handleFolderSelect = (e) => {
    const selectedFiles = Array.from(e.target.files);
    if (selectedFiles.length === 0) return;
    
    setFiles(selectedFiles);
    setDownloadReady(false);
    setZipBlob(null);
    setCompressionProgress(0);
  };

  // Processing filter engine to dynamically separate metrics assets
  const getFilteredFiles = () => {
    const ignoredList = getIgnoredList();
    return files.filter(file => {
      // Extract file components structural relative context system
      const relativePath = file.webkitRelativePath || file.name;
      const pathParts = relativePath.split('/');
      
      // Match rules to inspect if path matches exclusion configurations
      return !pathParts.some(part => ignoredList.includes(part));
    });
  };

  const getExcludedFilesCount = () => {
    return files.length - getFilteredFiles().length;
  };

  // Generate dynamic runtime client side compression zip package
  const handleGenerateZip = async () => {
    const filteredFiles = getFilteredFiles();
    if (filteredFiles.length === 0) return;

    setIsProcessing(true);
    setCompressionProgress(1);
    
    const zip = new JSZip();

    try {
      // Loop over active filtered array and push direct buffers into zip constructor block
      for (let i = 0; i < filteredFiles.length; i++) {
        const file = filteredFiles[i];
        const relativePath = file.webkitRelativePath || file.name;
        
        // Read file contents as binary blobs natively inside client sandbox context
        zip.file(relativePath, file);
        
        // Calculate progress percentage linearly
        const currentProgress = Math.round(((i + 1) / filteredFiles.length) * 100);
        setCompressionProgress(currentProgress);
      }

      // Generate localized data binary outputs wrapper block
      const contentBlob = await zip.generateAsync({ type: 'blob' }, (metadata) => {
        if (metadata.currentFile) {
          // Adjust state smoothly over large structures
          setCompressionProgress(Math.round(metadata.percent));
        }
      });

      setZipBlob(contentBlob);
      setDownloadReady(true);
    } catch (error) {
      console.error("Browser zip compilation crashed inside dynamic execution container:", error);
      alert("Compression failed. Clear application space memory parameters and try again.");
    } finally {
      setIsProcessing(false);
    }
  };

  const triggerDownload = () => {
    if (!zipBlob) return;
    saveAs(zipBlob, 'indicatorhub-export-package.zip');
  };

  return (
    <div className="max-w-4xl mx-auto my-8 p-6 bg-slate-900 border border-slate-800 rounded-xl shadow-xl">
      <div className="flex items-center gap-3 border-b border-slate-800 pb-4 mb-6">
        <div className="bg-amber-500/10 text-amber-500 p-2.5 rounded-lg">
          <Layers className="h-6 w-6" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-slate-100">Project Workspace Backup Tool</h2>
          <p className="text-xs text-slate-400">Pure Client-side localized compilation engine. Your source assets never upload to external servers.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Left Interactive Control Panel Box */}
        <div className="md:col-span-1 space-y-6">
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              1. Choose Source Directory
            </label>
            <input
              type="file"
              ref={fileInputRef}
              webkitdirectory="true"
              directory="true"
              multiple
              onChange={handleFolderSelect}
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current.click()}
              className="w-full flex items-center justify-center gap-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 py-3 px-4 rounded-lg font-medium transition cursor-pointer text-sm"
            >
              <FolderUp className="h-4 w-4 text-amber-500" />
              <span>Select Project Folder</span>
            </button>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              2. Ignore Rules (Comma Separated)
            </label>
            <textarea
              rows={3}
              value={ignoredInput}
              onChange={(e) => {
                setIgnoredInput(e.target.value);
                setDownloadReady(false);
              }}
              placeholder="e.g., node_modules, dist, .env"
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm text-slate-200 placeholder-slate-700 focus:outline-none focus:border-amber-500 font-mono resize-none"
            />
            <span className="text-[10px] text-slate-500 mt-1 block">
              In names ko system paths ke andar ignore kar diya jayega.
            </span>
          </div>

          {files.length > 0 && !downloadReady && (
            <button
              onClick={handleGenerateZip}
              disabled={isProcessing}
              className="w-full flex items-center justify-center gap-2 bg-amber-600 hover:bg-amber-500 disabled:bg-slate-800 text-slate-950 font-bold py-3 px-4 rounded-lg transition shadow-lg text-sm"
            >
              {isProcessing ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  <span>Processing ({compressionProgress}%)</span>
                </>
              ) : (
                <>
                  <Archive className="h-4 w-4" />
                  <span>Compile Filtered ZIP</span>
                </>
              )}
            </button>
          )}

          {downloadReady && (
            <button
              onClick={triggerDownload}
              className="w-full flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3 px-4 rounded-lg transition shadow-lg text-sm animate-pulse"
            >
              <Archive className="h-4 w-4" />
              <span>Download Complete ZIP</span>
            </button>
          )}
        </div>

        {/* Right Active Visualization Panel Box */}
        <div className="md:col-span-2 bg-slate-950 border border-slate-800 rounded-lg p-4 flex flex-col justify-between min-h-[250px]">
          <div>
            <div className="flex items-center justify-between border-b border-slate-900 pb-2 mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">File Sync Mapping Manifest</span>
              <span className="text-xs font-mono text-slate-500">{getFilteredFiles().length} Active Files</span>
            </div>

            {files.length === 0 ? (
              <div className="h-40 flex flex-col items-center justify-center text-slate-600 text-sm italic">
                No folder source linked. Select folder directory tree above to map artifacts.
              </div>
            ) : (
              <div className="max-h-52 overflow-y-auto text-xs font-mono space-y-1 pr-2 scrollbar-thin scrollbar-thumb-slate-800">
                {getFilteredFiles().slice(0, 100).map((file, idx) => (
                  <div key={idx} className="flex items-center gap-2 text-slate-300 py-0.5 truncate border-b border-slate-900/50">
                    <FileCheck className="h-3 w-3 text-emerald-500 shrink-0" />
                    <span className="truncate">{file.webkitRelativePath || file.name}</span>
                  </div>
                ))}
                {getFilteredFiles().length > 100 && (
                  <div className="text-[10px] text-amber-500 pt-1 tracking-wider italic">
                    ... aur {getFilteredFiles().length - 100} mazeed files file array payload mapping systems mein active hain.
                  </div>
                )}
              </div>
            )}
          </div>

          {files.length > 0 && (
            <div className="mt-4 pt-3 border-t border-slate-900 flex items-center justify-between text-xs font-medium">
              <div className="flex items-center gap-2 text-slate-400">
                <span>Total Detected: <strong className="text-slate-200">{files.length}</strong></span>
              </div>
              <div className="flex items-center gap-1.5 text-rose-500 bg-rose-500/5 px-2.5 py-1 rounded-md border border-rose-500/10">
                <FileX className="h-3.5 w-3.5" />
                <span>Ignored Filters: <strong>{getExcludedFilesCount()} files</strong></span>
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}










// const fs = require('fs');
// const path = require('path');
// const archiver = require('archiver');

// /**
//  * CONFIGURATION CONFIG:
//  * Yahan aap choose kar sakte hain ki kis folder ko zip karna hai aur kya skip karna hai.
//  */
// const CONFIG = {
//   sourceDir: path.join(__dirname, './frontend'), // Aapke frontend folder ka path (Change text if needed)
//   outputFile: path.join(__dirname, './frontend-project.zip'), // Output zip file ka naam
  
//   // ADVANCED FEATURE: Jo chizen aapko zip MEIN NAHI CHAHIYE, unhe yahan dalein
//   // Yeh directory names aur file names dono par kaam karega
//   ignoredNames: [
//     'node_modules',
//     '.git',
//     '.github',
//     'dist',
//     'build',
//     '.DS_Store',
//     '.env',
//     '.env.local',
//     'npm-debug.log'
//   ]
// };

// function zipFolder(config) {
//   // 1. Check karein ki source directory exist karti hai ya nahi
//   if (!fs.existsSync(config.sourceDir)) {
//     console.error(`❌ Error: Source directory nahi mili: ${config.sourceDir}`);
//     process.exit(1);
//   }

//   console.log(`🚀 Compression shuru ho raha hai...`);
//   console.log(`📂 Source: ${config.sourceDir}`);
//   console.log(`📦 Output: ${config.outputFile}`);
//   console.log(`🚫 Ignoring: [${config.ignoredNames.join(', ')}]\n`);

//   // 2. Write stream create karein zip file generate karne ke liye
//   const output = fs.createWriteStream(config.outputFile);
//   const archive = archiver('zip', {
//     zlib: { level: 9 } // Level 9 matlab maximum compression (sabse choti file size)
//   });

//   // Listeners for tracking progress
//   output.on('close', () => {
//     const sizeInMB = (archive.pointer() / 1024 / 1024).toFixed(2);
//     console.log(`\n==============================================`);
//     console.log(`✅ Success! Zip file successfully create ho gayi.`);
//     console.log(`📊 Total Size: ${sizeInMB} MB`);
//     console.log(`==============================================`);
//   });

//   output.on('end', () => {
//     console.log('Data draining complete.');
//   });

//   archive.on('warning', (err) => {
//     if (err.code === 'ENOENT') {
//       console.warn(`⚠️ Warning: Some files were missing:`, err);
//     } else {
//       throw err;
//     }
//   });

//   archive.on('error', (err) => {
//     console.error(`❌ Compression Error:`, err);
//     throw err;
//   });

//   // Archive ko file output stream se connect karein
//   archive.pipe(output);

//   /**
//    * ADVANCED FILTRATION LOGIC
//    * Yeh function har file aur folder ko process karte waqt check karta hai 
//    * ki wo humari ignoredNames list mein hai ya nahi.
//    */
//   const filterFunction = (entry) => {
//     // Har file/folder ka relative path nikalen
//     const relativePath = path.relative(config.sourceDir, entry.name);
    
//     // Path ke har segment ko todkar check karein (e.g., 'src/node_modules/test' -> ['src', 'node_modules', 'test'])
//     const pathParts = relativePath.split(path.sep);

//     // Agar koi bhi part hamari ignore list mein match hota hai, to skip karein
//     const shouldIgnore = pathParts.some(part => config.ignoredNames.includes(part));

//     if (shouldIgnore) {
//       // Log line-by-line debugging ke liye temporary open kar sakte hain:
//       // console.log(`🚫 Skipped: ${relativePath}`);
//       return false; // Archiver isko ignore kar dega
//     }

//     // Agar folder nahi hai to log karein ki file add ho rahi hai
//     if (entry.stats.isFile()) {
//       console.log(`➕ Adding: ${relativePath}`);
//     }
    
//     return entry;
//   };

//   // पूरे folder ko archive mein add karein filter logic ke saath
//   archive.directory(config.sourceDir, false, filterFunction);

//   // Compression pipeline ko finalize karein
//   archive.finalize();
// }

// // Script ko run karein
// zipFolder(CONFIG);