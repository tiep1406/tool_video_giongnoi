import React, { useState, useEffect } from 'react';
import './index.css';

const DEFAULT_VOICES = [
  { id: 'vi-VN-HoaiMyNeural', name: 'Hoài My (Nữ - Tiếng Việt)', lang: 'vi-VN', gender: 'Female' },
  { id: 'vi-VN-NamMinhNeural', name: 'Nam Minh (Nam - Tiếng Việt)', lang: 'vi-VN', gender: 'Male' },
  { id: 'en-US-AvaNeural', name: 'Ava (Nữ - Tiếng Anh Mỹ)', lang: 'en-US', gender: 'Female' },
  { id: 'en-US-AndrewNeural', name: 'Andrew (Nam - Tiếng Anh Mỹ)', lang: 'en-US', gender: 'Male' },
  { id: 'en-US-EmmaNeural', name: 'Emma (Nữ - Tiếng Anh Mỹ)', lang: 'en-US', gender: 'Female' },
  { id: 'ja-JP-NanamiNeural', name: 'Nanami (Nữ - Tiếng Nhật)', lang: 'ja-JP', gender: 'Female' },
  { id: 'zh-CN-XiaoxiaoNeural', name: 'Xiaoxiao (Nữ - Tiếng Trung)', lang: 'zh-CN', gender: 'Female' }
];

function App() {
  const [activeTab, setActiveTab] = useState('video'); // 'video' | 'tts'
  
  // Video Generator State
  const [url, setUrl] = useState('');
  const [tone, setTone] = useState('Nghiêm túc');
  const [prompt, setPrompt] = useState('');
  const [videoVoice, setVideoVoice] = useState('vi-VN-HoaiMyNeural');
  const [isProcessing, setIsProcessing] = useState(false);
  const [isRendering, setIsRendering] = useState(false);
  const [timeline, setTimeline] = useState(null);
  const [sessionData, setSessionData] = useState(null);
  const [videoUrl, setVideoUrl] = useState(null);
  const [sceneImages, setSceneImages] = useState({});
  const [scenePreviews, setScenePreviews] = useState({});
  const [historyList, setHistoryList] = useState([]);

  // TTS Studio State
  const [ttsMode, setTtsMode] = useState('preset'); // 'preset' | 'standard' | 'clone'
  const [voices, setVoices] = useState(DEFAULT_VOICES);
  const [presets, setPresets] = useState([]);
  const [selectedPresetId, setSelectedPresetId] = useState('preset_nam_review_phim');
  const [voiceSearch, setVoiceSearch] = useState('');
  const [ttsText, setTtsText] = useState('Chào mừng quý vị và các bạn đã đến với công cụ chuyển đổi văn bản thành giọng nói AI.');
  const [ttsVoice, setTtsVoice] = useState('vi-VN-HoaiMyNeural');
  const [ttsRate, setTtsRate] = useState('+0%');
  const [ttsPitch, setTtsPitch] = useState('+0Hz');
  const [sampleFile, setSampleFile] = useState(null);
  const [sampleFileUrl, setSampleFileUrl] = useState(null);
  const [sampleLanguage, setSampleLanguage] = useState('vi');
  const [sampleGender, setSampleGender] = useState('auto'); // 'auto' | 'male' | 'female'
  const [elevenLabsApiKey, setElevenLabsApiKey] = useState(() => localStorage.getItem('elevenlabs_api_key') || '');
  
  // Import Custom Voice State
  const [showImportModal, setShowImportModal] = useState(false);
  const [customVoiceName, setCustomVoiceName] = useState('');
  const [customVoiceFile, setCustomVoiceFile] = useState(null);
  const [customVoiceGender, setCustomVoiceGender] = useState('male');
  const [customVoiceLang, setCustomVoiceLang] = useState('vi');
  const [isImportingVoice, setIsImportingVoice] = useState(false);

  const [ttsIsProcessing, setTtsIsProcessing] = useState(false);
  const [ttsAudioUrl, setTtsAudioUrl] = useState(null);
  const [ttsHistory, setTtsHistory] = useState([]);

  // Video Downloader State
  const [dlUrl, setDlUrl] = useState('');
  const [dlFormat, setDlFormat] = useState('best');
  const [dlInfo, setDlInfo] = useState(null);
  const [isFetchingInfo, setIsFetchingInfo] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [dlProgressMsg, setDlProgressMsg] = useState('');
  const [downloadResult, setDownloadResult] = useState(null);
  const [dlHistory, setDlHistory] = useState([]);


  const fetchHistory = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/history');
      const data = await res.json();
      setHistoryList(data.history || []);
    } catch(e) {}
  };

  const fetchVoices = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/tts/voices');
      if (res.ok) {
        const data = await res.json();
        if (data.voices && data.voices.length > 0) {
          setVoices(data.voices);
        }
      }
    } catch (e) {}
  };

  const fetchPresets = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/tts/presets');
      if (res.ok) {
        const data = await res.json();
        setPresets(data.presets || []);
      }
    } catch (e) {}
  };

  useEffect(() => {
    fetchHistory();
    fetchVoices();
    fetchPresets();
  }, []);

  const handleApiKeyChange = (e) => {
    const val = e.target.value;
    setElevenLabsApiKey(val);
    localStorage.setItem('elevenlabs_api_key', val);
  };

  const handleImportCustomVoice = async () => {
    if (!customVoiceName.trim()) {
      alert("Vui lòng nhập tên cho giọng nói mới!");
      return;
    }
    if (!customVoiceFile) {
      alert("Vui lòng tải lên file MP3/WAV âm thanh mẫu!");
      return;
    }

    setIsImportingVoice(true);
    const formData = new FormData();
    formData.append('name', customVoiceName);
    formData.append('gender', customVoiceGender);
    formData.append('language', customVoiceLang);
    formData.append('sample_file', customVoiceFile);

    try {
      const res = await fetch('http://localhost:8000/api/tts/import_custom_voice', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (res.ok) {
        alert(`🎉 Đã lưu thành công giọng "${customVoiceName}" vào danh sách!`);
        setCustomVoiceName('');
        setCustomVoiceFile(null);
        setShowImportModal(false);
        await fetchVoices();
        if (data.voice?.id) {
          setTtsVoice(data.voice.id);
          setVideoVoice(data.voice.id);
        }
      } else {
        alert("Lỗi import giọng: " + (data.detail || "Không rõ nguyên nhân"));
      }
    } catch (e) {
      alert("Lỗi kết nối máy chủ khi import giọng.");
    }
    setIsImportingVoice(false);
  };

  const filteredVoices = voices.filter(v => 
    v.name.toLowerCase().includes(voiceSearch.toLowerCase()) || 
    v.id.toLowerCase().includes(voiceSearch.toLowerCase()) ||
    v.lang.toLowerCase().includes(voiceSearch.toLowerCase())
  );

  const loadSession = async (session_id) => {
    try {
      const res = await fetch(`http://localhost:8000/api/history/${session_id}`);
      if (!res.ok) return;
      const data = await res.json();
      
      setUrl(data.url || '');
      setTimeline(data.storyboard || []);
      setSessionData({
        session_id: data.session_id,
        source_info: data.source_info
      });
      setSceneImages(data.scene_images || {});
      setVideoUrl(data.video_url || null);
    } catch(e) {}
  };

  const handleGenerate = async () => {
    setIsProcessing(true);
    setVideoUrl(null);
    try {
      const response = await fetch('http://localhost:8000/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, tone, prompt })
      });
      
      const data = await response.json();
      if (!response.ok) {
        alert("Lỗi: " + (data.detail || "Không thể tạo kịch bản"));
        setIsProcessing(false);
        return;
      }
      
      const formattedTimeline = (data.storyboard || []).map((item, index) => ({
        ...item,
        time: `0:0${index * 5}`
      }));
      setTimeline(formattedTimeline);
      setSessionData({
        session_id: data.session_id,
        source_info: data.source_info
      });
      fetchHistory();
    } catch (err) {
      alert("Lỗi kết nối Server. Vui lòng đảm bảo backend đang chạy.");
    }
    setIsProcessing(false);
  };

  const handleImageUpload = async (sceneIndex, event) => {
    const file = event.target.files[0];
    if (!file || !sessionData?.session_id) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await fetch(`http://localhost:8000/api/upload_scene_image/${sessionData.session_id}/${sceneIndex}`, {
        method: 'POST',
        body: formData
      });
      const data = await response.json();
      if (response.ok) {
        setSceneImages(prev => ({
          ...prev,
          [sceneIndex]: URL.createObjectURL(file)
        }));
      } else {
        alert("Lỗi tải ảnh: " + data.detail);
      }
    } catch (err) {
      alert("Lỗi kết nối khi tải ảnh lên.");
    }
  };

  const handlePreviewSceneAudio = async (sceneIndex, scriptText) => {
    setScenePreviews(prev => ({ ...prev, [sceneIndex]: { ...prev[sceneIndex], isLoading: true } }));
    try {
      const res = await fetch('http://localhost:8000/api/tts/preview_scene', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: scriptText,
          voice: videoVoice
        })
      });
      const data = await res.json();
      if (res.ok && data.audio_url) {
        setScenePreviews(prev => ({
          ...prev,
          [sceneIndex]: { audioUrl: data.audio_url, isLoading: false }
        }));
      } else {
        alert("Lỗi tạo âm thanh: " + (data.detail || "Không rõ nguyên nhân"));
        setScenePreviews(prev => ({ ...prev, [sceneIndex]: { ...prev[sceneIndex], isLoading: false } }));
      }
    } catch (e) {
      alert("Lỗi kết nối Server khi nghe thử.");
      setScenePreviews(prev => ({ ...prev, [sceneIndex]: { ...prev[sceneIndex], isLoading: false } }));
    }
  };

  const handleRender = async () => {
    setIsRendering(true);
    try {
      const response = await fetch('http://localhost:8000/api/render', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionData.session_id,
          storyboard: timeline,
          source_info: sessionData.source_info,
          voice: videoVoice
        })
      });
      
      const data = await response.json();
      if (!response.ok) {
        alert("Lỗi Render: " + (data.detail || "Không rõ nguyên nhân"));
      } else {
        setVideoUrl(data.video_url);
      }
    } catch (err) {
      alert("Lỗi kết nối Server khi Render.");
    }
    setIsRendering(false);
  };

  const handleSampleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSampleFile(file);
      setSampleFileUrl(URL.createObjectURL(file));
    }
  };

  const handlePresetGenerate = async () => {
    if (!ttsText.trim()) {
      alert("Vui lòng nhập văn bản cần chuyển đổi!");
      return;
    }
    setTtsIsProcessing(true);
    setTtsAudioUrl(null);
    try {
      const response = await fetch('http://localhost:8000/api/tts/generate_preset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          preset_id: selectedPresetId,
          text: ttsText
        })
      });

      const data = await response.json();
      if (!response.ok) {
        alert("Lỗi sinh giọng: " + (data.detail || "Không thể tạo giọng đọc"));
      } else {
        setTtsAudioUrl(data.audio_url);
        const pObj = presets.find(p => p.id === selectedPresetId);
        setTtsHistory(prev => [
          {
            id: data.file_id,
            text: ttsText.length > 50 ? ttsText.substring(0, 50) + '...' : ttsText,
            voiceName: pObj ? pObj.name : selectedPresetId,
            audioUrl: data.audio_url,
            time: new Date().toLocaleTimeString('vi-VN')
          },
          ...prev
        ]);
      }
    } catch (err) {
      alert("Lỗi kết nối máy chủ.");
    }
    setTtsIsProcessing(false);
  };

  const handleTTSGenerate = async () => {
    if (!ttsText.trim()) {
      alert("Vui lòng nhập văn bản cần chuyển đổi!");
      return;
    }
    setTtsIsProcessing(true);
    setTtsAudioUrl(null);
    try {
      const response = await fetch('http://localhost:8000/api/tts/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: ttsText,
          voice: ttsVoice,
          rate: ttsRate,
          pitch: ttsPitch
        })
      });

      const data = await response.json();
      if (!response.ok) {
        alert("Lỗi TTS: " + (data.detail || "Không thể tạo giọng nói"));
      } else {
        setTtsAudioUrl(data.audio_url);
        const selectedVoiceObj = voices.find(v => v.id === ttsVoice);
        setTtsHistory(prev => [
          {
            id: data.file_id,
            text: ttsText.length > 50 ? ttsText.substring(0, 50) + '...' : ttsText,
            voiceName: selectedVoiceObj ? selectedVoiceObj.name : ttsVoice,
            audioUrl: data.audio_url,
            time: new Date().toLocaleTimeString('vi-VN')
          },
          ...prev
        ]);
      }
    } catch (err) {
      alert("Lỗi kết nối đến máy chủ TTS.");
    }
    setTtsIsProcessing(false);
  };

  const handleTTSClone = async () => {
    if (!ttsText.trim()) {
      alert("Vui lòng nhập văn bản cần nhái giọng!");
      return;
    }
    if (!sampleFile) {
      alert("Vui lòng tải lên file MP3/WAV giọng mẫu!");
      return;
    }
    setTtsIsProcessing(true);
    setTtsAudioUrl(null);

    const formData = new FormData();
    formData.append('text', ttsText);
    formData.append('language', sampleLanguage);
    formData.append('gender', sampleGender);
    formData.append('api_key', elevenLabsApiKey);
    formData.append('sample_file', sampleFile);

    try {
      const response = await fetch('http://localhost:8000/api/tts/clone', {
        method: 'POST',
        body: formData
      });

      const data = await response.json();
      if (!response.ok) {
        alert("Lỗi nhái giọng: " + (data.detail || "Không thể sinh giọng nhái"));
      } else {
        setTtsAudioUrl(data.audio_url);
        const engineLabel = elevenLabsApiKey ? '🌟 ElevenLabs 98%' : '🤖 OmniVoice Local';
        setTtsHistory(prev => [
          {
            id: data.file_id,
            text: ttsText.length > 50 ? ttsText.substring(0, 50) + '...' : ttsText,
            voiceName: `${engineLabel} (${sampleFile.name})`,
            audioUrl: data.audio_url,
            time: new Date().toLocaleTimeString('vi-VN')
          },
          ...prev
        ]);
      }
    } catch (err) {
      alert("Lỗi kết nối máy chủ nhái giọng.");
    }
    setTtsIsProcessing(false);
  };

  const handleFetchDlInfo = async () => {
    if (!dlUrl || !dlUrl.trim()) {
      alert("Vui lòng nhập đường dẫn video!");
      return;
    }
    setIsFetchingInfo(true);
    setDlInfo(null);
    setDownloadResult(null);
    try {
      const res = await fetch('http://localhost:8000/api/downloader/info', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: dlUrl.trim() })
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        setDlInfo(data);
      } else {
        alert("Lỗi: " + (data.detail || data.message || "Không thể lấy thông tin video"));
      }
    } catch (e) {
      alert("Lỗi kết nối máy chủ backend.");
    }
    setIsFetchingInfo(false);
  };

  const handleStartDownload = async () => {
    if (!dlUrl || !dlUrl.trim()) {
      alert("Vui lòng nhập đường dẫn video!");
      return;
    }
    setIsDownloading(true);
    setDownloadResult(null);
    setDlProgressMsg('Đang tiến hành tải xuống video và xử lý định dạng...');
    try {
      const res = await fetch('http://localhost:8000/api/downloader/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: dlUrl.trim(), format_choice: dlFormat })
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        setDownloadResult(data);
        setDlHistory(prev => [data, ...prev]);
      } else {
        alert("Lỗi tải video: " + (data.detail || data.message || "Không thể tải video từ link này"));
      }
    } catch (e) {
      alert("Lỗi kết nối máy chủ backend khi tải video.");
    }
    setIsDownloading(false);
  };

  return (
    <div className="min-h-screen p-8 animate-fade-in" style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
      {/* Header */}
      <header style={{ textAlign: 'center', marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2.5rem', fontWeight: '700', marginBottom: '0.5rem', background: '-webkit-linear-gradient(#fff, #94a3b8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
          AI Video & Text-to-Speech Studio
        </h1>
        <p style={{ color: 'var(--text-muted)' }}>Tự động hóa luồng sản xuất video & thư viện 300+ giọng nói AI tức thời (Portable 100%)</p>
      </header>

      {/* Nav Tabs */}
      <nav className="nav-tabs">
        <button 
          className={`tab-btn ${activeTab === 'video' ? 'active' : ''}`}
          onClick={() => setActiveTab('video')}
        >
          📺 Tạo Video từ Tin Tức
        </button>
        <button 
          className={`tab-btn ${activeTab === 'tts' ? 'active' : ''}`}
          onClick={() => setActiveTab('tts')}
        >
          🎙️ Studio Giọng Nói Tiếng Việt & Đa Ngôn Ngữ
        </button>
        <button 
          className={`tab-btn ${activeTab === 'downloader' ? 'active' : ''}`}
          onClick={() => setActiveTab('downloader')}
        >
          📥 Tải Video Từ Link (YouTube, TikTok, FB...)
        </button>
      </nav>

      {/* TAB 1: News Video Generator */}
      {activeTab === 'video' && (
        <div style={{ display: 'grid', gridTemplateColumns: '250px 1fr 1fr', gap: '2rem' }}>
          {/* Lịch sử */}
          <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column' }}>
            <h2 style={{ marginBottom: '1rem', fontSize: '1.1rem', color: 'var(--accent)' }}>📚 Lịch sử Render</h2>
            <div style={{ flex: 1, overflowY: 'auto' }}>
              {historyList.length === 0 ? (
                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Chưa có dự án nào.</p>
              ) : (
                historyList.map(h => (
                  <div key={h.session_id} 
                       onClick={() => loadSession(h.session_id)}
                       style={{
                         padding: '0.75rem',
                         marginBottom: '0.5rem',
                         background: sessionData?.session_id === h.session_id ? 'rgba(56, 189, 248, 0.2)' : 'rgba(0,0,0,0.2)',
                         borderRadius: '6px',
                         cursor: 'pointer',
                         border: sessionData?.session_id === h.session_id ? '1px solid var(--accent)' : '1px solid transparent'
                       }}>
                    <div style={{ fontWeight: '600', fontSize: '0.85rem', marginBottom: '4px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {h.title}
                    </div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                      {new Date(h.timestamp).toLocaleString('vi-VN')}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Form Thông tin Nguồn */}
          <div className="glass-panel" style={{ padding: '2rem' }}>
            <h2 style={{ marginBottom: '1.5rem', fontSize: '1.25rem' }}>1. Thông tin Nguồn</h2>
            
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>URL Bài báo / YouTube</label>
              <input type="text" placeholder="https://..." value={url} onChange={e => setUrl(e.target.value)} />
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>Giọng điệu (Tone)</label>
              <select value={tone} onChange={e => setTone(e.target.value)}>
                <option value="Nghiêm túc">Nghiêm túc (Bản tin)</option>
                <option value="Châm biếm">Châm biếm (Góc nhìn đa chiều)</option>
                <option value="Hài hước">Hài hước (Giải trí)</option>
                <option value="Khách quan">Khách quan (Phóng sự)</option>
              </select>
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>🎙️ Chọn Giọng Đọc Video</label>
              <select value={videoVoice} onChange={e => setVideoVoice(e.target.value)}>
                {filteredVoices.map(v => (
                  <option key={v.id} value={v.id}>{v.name}</option>
                ))}
              </select>
            </div>

            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>Chỉ thị thêm (Prompt)</label>
              <textarea rows="3" placeholder="Ví dụ: Tập trung vào phản ứng của cộng đồng mạng..." value={prompt} onChange={e => setPrompt(e.target.value)}></textarea>
            </div>

            <button className="btn-primary" style={{ width: '100%', padding: '12px' }} onClick={handleGenerate} disabled={isProcessing || !url}>
              {isProcessing ? 'Đang phân tích AI...' : 'Tạo Kịch Bản & Timeline'}
            </button>
          </div>

          {/* Timeline & Render */}
          <div className="glass-panel" style={{ padding: '2rem', display: 'flex', flexDirection: 'column' }}>
            <h2 style={{ marginBottom: '1.5rem', fontSize: '1.25rem' }}>2. Kịch bản & Phân Cảnh</h2>
            
            {!timeline ? (
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', border: '1px dashed var(--border-color)', borderRadius: '8px' }}>
                Chưa có dữ liệu. Vui lòng nhập URL và Tạo Kịch Bản.
              </div>
            ) : (
              <div style={{ flex: 1, overflowY: 'auto', paddingRight: '10px' }}>
                {timeline.map((item, idx) => (
                  <div key={idx} style={{ 
                    background: 'rgba(0,0,0,0.2)', 
                    padding: '1rem', 
                    borderRadius: '8px', 
                    marginBottom: '1rem', 
                    borderLeft: '3px solid var(--accent)',
                    position: 'relative',
                    overflow: 'hidden'
                  }}>
                    {sceneImages[idx] && (
                       <div style={{
                         position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
                         backgroundImage: `url(${sceneImages[idx]})`,
                         backgroundSize: 'cover',
                         backgroundPosition: 'center',
                         opacity: 0.15,
                         zIndex: 0
                       }}></div>
                    )}
                    <div style={{ position: 'relative', zIndex: 1 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                        <span style={{ fontWeight: '600', fontSize: '0.875rem', color: 'var(--accent)' }}>Cảnh {item.scene}</span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{item.time}</span>
                      </div>
                      <p style={{ fontSize: '0.95rem', marginBottom: '0.5rem', lineHeight: '1.5' }}>"{item.script}"</p>
                      <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>📷 Mô tả AI: {item.visual_cue}</p>
                      
                      {/* Audio preview per scene */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', margin: '0.5rem 0', flexWrap: 'wrap' }}>
                        <button 
                          onClick={() => handlePreviewSceneAudio(idx, item.script)}
                          disabled={scenePreviews[idx]?.isLoading}
                          style={{ fontSize: '0.75rem', background: 'rgba(59, 130, 246, 0.2)', color: '#38bdf8', padding: '4px 10px', borderRadius: '4px' }}
                        >
                          {scenePreviews[idx]?.isLoading ? '⏳ Đang tạo audio...' : '🔊 Nghe thử Giọng Đọc'}
                        </button>

                        {scenePreviews[idx]?.audioUrl && (
                          <audio controls src={scenePreviews[idx].audioUrl} style={{ height: '30px', width: '220px' }}></audio>
                        )}
                      </div>

                      <div style={{ marginTop: '0.5rem' }}>
                         <label style={{ fontSize: '0.75rem', color: 'var(--accent)', cursor: 'pointer', display: 'inline-block', padding: '4px 8px', background: 'rgba(56, 189, 248, 0.1)', borderRadius: '4px' }}>
                            + Upload Ảnh Riêng
                            <input type="file" accept="image/*" style={{ display: 'none' }} onChange={(e) => handleImageUpload(idx, e)} />
                         </label>
                         {sceneImages[idx] && <span style={{ fontSize: '0.75rem', marginLeft: '8px', color: '#10b981' }}>Đã tải lên ✓</span>}
                      </div>
                    </div>
                  </div>
                ))}
                
                <button className="btn-primary" 
                  style={{ width: '100%', marginTop: '1rem', background: '#10b981', boxShadow: '0 4px 14px 0 rgba(16, 185, 129, 0.39)' }}
                  onClick={handleRender}
                  disabled={isRendering}
                >
                  {isRendering ? 'Đang Render (Vui lòng đợi)...' : 'Render Video Cuối Cùng'}
                </button>

                {videoUrl && (
                  <div style={{ marginTop: '1.5rem', textAlign: 'center' }}>
                    <h3 style={{ marginBottom: '1rem', color: '#10b981' }}>🎉 Render Thành Công!</h3>
                    <video controls width="100%" src={videoUrl} style={{ borderRadius: '8px', border: '1px solid var(--border-color)' }}></video>
                    <a href={videoUrl} download target="_blank" rel="noreferrer" style={{ display: 'inline-block', marginTop: '1rem', color: 'var(--accent)', textDecoration: 'none' }}>Tải Video Xuống</a>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: TTS Studio & Voice Cloning */}
      {activeTab === 'tts' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: '2rem' }}>
          {/* TTS Form */}
          <div className="glass-panel" style={{ padding: '2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h2 style={{ fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                🎙️ Studio Giọng Nói AI
              </h2>

              {/* Mode Selector */}
              <div className="option-group">
                <button 
                  className={`chip-btn ${ttsMode === 'preset' ? 'selected' : ''}`}
                  onClick={() => setTtsMode('preset')}
                >
                  🇻🇳 8+ Mẫu Giọng Tiếng Việt
                </button>
                <button 
                  className={`chip-btn ${ttsMode === 'standard' ? 'selected' : ''}`}
                  onClick={() => setTtsMode('standard')}
                >
                  🌐 Thư Viện {voices.length}+ Giọng
                </button>
                <button 
                  className={`chip-btn ${ttsMode === 'clone' ? 'selected' : ''}`}
                  onClick={() => setTtsMode('clone')}
                >
                  🎭 Nhái Giọng MP3
                </button>
              </div>
            </div>

            {/* Mode 0: Vietnamese Presets (Review Phim, Thời Sự, TikTok, Truyện...) */}
            {ttsMode === 'preset' && (
              <>
                <div style={{ marginBottom: '1.25rem' }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', color: '#38bdf8', fontWeight: '600', fontSize: '0.9rem' }}>
                    1. Chọn Mẫu Phong Cách Giọng Đọc Tiếng Việt
                  </label>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                    {presets.map(p => (
                      <div 
                        key={p.id}
                        onClick={() => setSelectedPresetId(p.id)}
                        style={{
                          padding: '0.85rem',
                          borderRadius: '8px',
                          border: selectedPresetId === p.id ? '2px solid #38bdf8' : '1px solid var(--border-color)',
                          background: selectedPresetId === p.id ? 'rgba(56, 189, 248, 0.15)' : 'rgba(0,0,0,0.2)',
                          cursor: 'pointer',
                          transition: 'all 0.2s ease'
                        }}
                      >
                        <div style={{ fontWeight: '600', fontSize: '0.9rem', marginBottom: '4px', color: '#f8fafc' }}>
                          {p.name}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: '1.4' }}>
                          {p.description}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Input Text */}
                <div style={{ marginBottom: '1.25rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                    <label style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>2. Văn bản tiếng Việt cần đọc</label>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{ttsText.length} ký tự</span>
                  </div>
                  <textarea 
                    rows="4" 
                    placeholder="Nhập văn bản tiếng Việt bạn muốn tạo giọng đọc..."
                    value={ttsText}
                    onChange={e => setTtsText(e.target.value)}
                    style={{ fontSize: '1rem', lineHeight: '1.6' }}
                  />
                </div>

                <button 
                  className="btn-primary" 
                  style={{ width: '100%', padding: '14px', fontSize: '1.05rem', fontWeight: '600', background: '#0284c7', boxShadow: '0 4px 14px rgba(2, 132, 199, 0.4)' }}
                  onClick={handlePresetGenerate}
                  disabled={ttsIsProcessing || !ttsText.trim()}
                >
                  {ttsIsProcessing ? '⚡ Đang Tạo Giọng Đọc Mẫu Tiếng Việt...' : '🇻🇳 Tạo Giọng Đọc Tiếng Việt Ngay'}
                </button>
              </>
            )}

            {/* Mode 1: Standard TTS */}
            {ttsMode === 'standard' && (
              <>
                {/* Import Custom Voice Banner */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', padding: '0.75rem 1rem', background: 'rgba(56, 189, 248, 0.1)', border: '1px solid rgba(56, 189, 248, 0.3)', borderRadius: '8px' }}>
                  <div>
                    <div style={{ fontSize: '0.9rem', fontWeight: '600', color: '#38bdf8' }}>➕ Thêm Giọng Nói Riêng Vào Danh Sách</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Tải file MP3 bất kỳ để tạo giọng dùng mãi mãi trong menu</div>
                  </div>
                  <button 
                    onClick={() => setShowImportModal(!showImportModal)}
                    style={{ padding: '6px 12px', fontSize: '0.8rem', background: '#38bdf8', color: '#0f172a', fontWeight: '600', borderRadius: '6px', border: 'none', cursor: 'pointer' }}
                  >
                    {showImportModal ? 'Đóng Form' : '+ Import Giọng Mới'}
                  </button>
                </div>

                {/* Import Modal / Form */}
                {showImportModal && (
                  <div style={{ background: 'rgba(15, 23, 42, 0.95)', border: '1px solid #38bdf8', padding: '1.25rem', borderRadius: '8px', marginBottom: '1.5rem' }}>
                    <h3 style={{ fontSize: '1rem', color: '#38bdf8', marginBottom: '0.75rem' }}>➕ Import File MP3 Giọng Đọc Mới</h3>
                    
                    <div style={{ marginBottom: '0.75rem' }}>
                      <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Tên giọng nói (Hiển thị trong menu):</label>
                      <input 
                        type="text" 
                        placeholder="Ví dụ: Giọng Thầy Giáo Hùng, Giọng MC Huyền..." 
                        value={customVoiceName}
                        onChange={e => setCustomVoiceName(e.target.value)}
                        style={{ padding: '8px', fontSize: '0.85rem' }}
                      />
                    </div>

                    <div style={{ marginBottom: '0.75rem' }}>
                      <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '4px' }}>File MP3 / WAV mẫu (3 - 15 giây):</label>
                      <input 
                        type="file" 
                        accept="audio/*" 
                        onChange={e => setCustomVoiceFile(e.target.files[0])}
                        style={{ fontSize: '0.8rem' }}
                      />
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1rem' }}>
                      <div>
                        <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Giới tính:</label>
                        <select value={customVoiceGender} onChange={e => setCustomVoiceGender(e.target.value)} style={{ padding: '6px' }}>
                          <option value="male">👨 Giọng Nam</option>
                          <option value="female">👩 Giọng Nữ</option>
                        </select>
                      </div>

                      <div>
                        <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Ngôn ngữ phát âm:</label>
                        <select value={customVoiceLang} onChange={e => setCustomVoiceLang(e.target.value)} style={{ padding: '6px' }}>
                          <option value="vi">Tiếng Việt</option>
                          <option value="en">Tiếng Anh</option>
                        </select>
                      </div>
                    </div>

                    <button 
                      onClick={handleImportCustomVoice}
                      disabled={isImportingVoice || !customVoiceName.trim() || !customVoiceFile}
                      style={{ width: '100%', padding: '10px', background: '#10b981', color: '#fff', fontWeight: '600', borderRadius: '6px', border: 'none', cursor: 'pointer' }}
                    >
                      {isImportingVoice ? '⏳ Đang Lưu Giọng Vào Dự Án...' : '💾 Lưu Giọng Nói Vào Dự Án Vĩnh Viễn'}
                    </button>
                  </div>
                )}

                {/* Input Text */}
                <div style={{ marginBottom: '1.25rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                    <label style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Nội dung văn bản</label>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{ttsText.length} ký tự</span>
                  </div>
                  <textarea 
                    rows="4" 
                    placeholder="Nhập hoặc dán văn bản bạn muốn chuyển đổi sang giọng nói..."
                    value={ttsText}
                    onChange={e => setTtsText(e.target.value)}
                    style={{ fontSize: '1rem', lineHeight: '1.6' }}
                  />
                </div>

                {/* Select Voice with Search */}
                <div style={{ marginBottom: '1.25rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                    <label style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>🌐 Chọn Giọng Đọc ({filteredVoices.length} / {voices.length} giọng)</label>
                  </div>
                  <input 
                    type="text" 
                    placeholder="🔍 Gõ để tìm giọng (vd: vi, nam, nu, ava, us, uk, ja)..." 
                    value={voiceSearch} 
                    onChange={e => setVoiceSearch(e.target.value)}
                    style={{ marginBottom: '0.5rem', padding: '8px 12px', fontSize: '0.85rem' }}
                  />
                  <select value={ttsVoice} onChange={e => setTtsVoice(e.target.value)} style={{ padding: '10px' }}>
                    {filteredVoices.map(v => (
                      <option key={v.id} value={v.id}>{v.name}</option>
                    ))}
                  </select>
                </div>

                {/* Options Grid: Speed & Pitch */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
                  <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>Tốc độ đọc (Speed)</label>
                    <div className="option-group">
                      {[
                        { label: '0.75x', val: '-25%' },
                        { label: '1.0x', val: '+0%' },
                        { label: '1.25x', val: '+25%' },
                        { label: '1.5x', val: '+50%' }
                      ].map(item => (
                        <button 
                          key={item.val} 
                          className={`chip-btn ${ttsRate === item.val ? 'selected' : ''}`}
                          onClick={() => setTtsRate(item.val)}
                        >
                          {item.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>Cao độ giọng (Pitch)</label>
                    <div className="option-group">
                      {[
                        { label: 'Trầm (-5Hz)', val: '-5Hz' },
                        { label: 'Chuẩn (0Hz)', val: '+0Hz' },
                        { label: 'Cao (+5Hz)', val: '+5Hz' }
                      ].map(item => (
                        <button 
                          key={item.val} 
                          className={`chip-btn ${ttsPitch === item.val ? 'selected' : ''}`}
                          onClick={() => setTtsPitch(item.val)}
                        >
                          {item.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Action Button */}
                <button 
                  className="btn-primary" 
                  style={{ width: '100%', padding: '14px', fontSize: '1.05rem', fontWeight: '600' }}
                  onClick={handleTTSGenerate}
                  disabled={ttsIsProcessing || !ttsText.trim()}
                >
                  {ttsIsProcessing ? '⚡ Đang chuyển đổi văn bản sang âm thanh...' : '🔊 Tạo Giọng Nói Ngay'}
                </button>
              </>
            )}

            {/* Mode 2: Voice Cloning (Sample MP3) */}
            {ttsMode === 'clone' && (
              <>
                {/* Free Engine Banner */}
                <div style={{ background: 'rgba(139, 92, 246, 0.15)', border: '1px solid rgba(139, 92, 246, 0.4)', padding: '1rem', borderRadius: '8px', marginBottom: '1.25rem' }}>
                  <div style={{ color: '#a78bfa', fontWeight: '600', fontSize: '0.9rem', marginBottom: '4px' }}>
                    🤖 Động Cơ Nhái Giọng OmniVoice (cosmichackerx/voice-cloner)
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#e2e8f0', lineHeight: '1.5' }}>
                    ✅ <b>Miễn Phí 100% - Không Giới Hạn Số Ký Tự - Không Cần Trả Phí</b>. Phân tích file mẫu MP3 và sinh ra giọng nói tiếng Việt chuẩn thần thái.
                  </div>
                </div>

                {/* ElevenLabs API Key Optional Input */}
                <div style={{ background: 'rgba(16, 185, 129, 0.08)', border: '1px dashed rgba(16, 185, 129, 0.3)', padding: '0.85rem', borderRadius: '8px', marginBottom: '1.25rem' }}>
                  <label style={{ display: 'block', marginBottom: '0.4rem', color: '#10b981', fontWeight: '600', fontSize: '0.85rem' }}>
                    🔑 ElevenLabs API Key (Tùy chọn nâng cao)
                  </label>
                  <input 
                    type="password" 
                    placeholder="Để trống nếu muốn dùng Động cơ Miễn phí ở trên..." 
                    value={elevenLabsApiKey}
                    onChange={handleApiKeyChange}
                    style={{ padding: '6px 10px', fontSize: '0.8rem' }}
                  />
                </div>

                <div style={{ background: 'rgba(59, 130, 246, 0.1)', border: '1px solid rgba(59, 130, 246, 0.3)', padding: '1rem', borderRadius: '8px', marginBottom: '1.25rem' }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', color: '#38bdf8', fontWeight: '600', fontSize: '0.9rem' }}>
                    1. Upload File MP3 / WAV Giọng Đọc Mẫu (3 - 25 Giây)
                  </label>
                  <input type="file" accept="audio/*" onChange={handleSampleFileChange} style={{ marginBottom: '0.5rem' }} />
                  {sampleFileUrl && (
                    <div style={{ marginTop: '0.5rem' }}>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Nghe thử file giọng mẫu đã tải lên:</span>
                      <audio controls src={sampleFileUrl} style={{ width: '100%', height: '36px' }}></audio>
                    </div>
                  )}
                </div>

                <div style={{ marginBottom: '1.25rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                    <label style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>2. Văn bản cần sinh ra theo giọng mẫu</label>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{ttsText.length} ký tự</span>
                  </div>
                  <textarea 
                    rows="4" 
                    placeholder="Nhập nội dung văn bản bạn muốn đọc theo giọng mẫu trên..."
                    value={ttsText}
                    onChange={e => setTtsText(e.target.value)}
                    style={{ fontSize: '1rem', lineHeight: '1.6' }}
                  />
                </div>

                {/* Options Grid: Language & Gender Selection */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
                  <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>Ngôn ngữ phát âm</label>
                    <select value={sampleLanguage} onChange={e => setSampleLanguage(e.target.value)}>
                      <option value="vi">Tiếng Việt (Vietnamese)</option>
                      <option value="en">Tiếng Anh (English)</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>Giới tính giọng mẫu</label>
                    <select value={sampleGender} onChange={e => setSampleGender(e.target.value)}>
                      <option value="auto">🔍 Tự động nhận diện (Auto Pitch)</option>
                      <option value="male">👨 Giọng Nam (Nam Minh)</option>
                      <option value="female">👩 Giọng Nữ (Hoài My)</option>
                    </select>
                  </div>
                </div>

                <button 
                  className="btn-primary" 
                  style={{ width: '100%', padding: '14px', fontSize: '1.05rem', fontWeight: '600', background: '#8b5cf6', boxShadow: '0 4px 14px rgba(139, 92, 246, 0.4)' }}
                  onClick={handleTTSClone}
                  disabled={ttsIsProcessing || !ttsText.trim() || !sampleFile}
                >
                  {ttsIsProcessing ? '🎭 AI Đang Nhái Giọng & Sinh Âm Thanh...' : '🎭 Nhái Giọng & Tạo Âm Thanh'}
                </button>
              </>
            )}

            {/* Main Result Audio */}
            {ttsAudioUrl && (
              <div className="audio-card">
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                  <span style={{ color: '#10b981', fontWeight: '600', fontSize: '0.95rem' }}>✅ Đã tạo âm thanh thành công!</span>
                  <a 
                    href={ttsAudioUrl} 
                    download={`tts_${Date.now()}.mp3`} 
                    target="_blank" 
                    rel="noreferrer"
                    style={{ background: 'rgba(16, 185, 129, 0.2)', color: '#10b981', padding: '6px 14px', borderRadius: '6px', textDecoration: 'none', fontSize: '0.85rem', fontWeight: '600' }}
                  >
                    ⬇️ Tải MP3
                  </a>
                </div>
                <audio controls autoPlay src={ttsAudioUrl} style={{ width: '100%', marginTop: '0.25rem' }}></audio>
              </div>
            )}
          </div>

          {/* History Panel */}
          <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column' }}>
            <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem', color: 'var(--accent)' }}>📜 Lịch sử tạo giọng nói</h3>
            
            <div style={{ flex: 1, overflowY: 'auto' }}>
              {ttsHistory.length === 0 ? (
                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Chưa có file âm thanh nào được tạo trong phiên làm việc này.</p>
              ) : (
                ttsHistory.map((item, idx) => (
                  <div key={idx} style={{ background: 'rgba(0,0,0,0.25)', padding: '0.85rem', borderRadius: '8px', marginBottom: '0.75rem', border: '1px solid var(--border-color)' }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: '500', marginBottom: '4px', color: '#f8fafc' }}>
                      "{item.text}"
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '6px', display: 'flex', justifyContent: 'space-between' }}>
                      <span>👤 {item.voiceName}</span>
                      <span>{item.time}</span>
                    </div>
                    <audio controls src={item.audioUrl} style={{ width: '100%', height: '32px' }}></audio>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: Universal Video Downloader */}
      {activeTab === 'downloader' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '2rem' }}>
          {/* Main Download Panel */}
          <div className="glass-panel" style={{ padding: '2rem' }}>
            <h2 style={{ marginBottom: '0.5rem', fontSize: '1.4rem', color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              📥 Tải Video Đa Nền Tảng Tự Động
            </h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
              Hỗ trợ dán link bất kỳ từ <strong>YouTube, TikTok, Facebook, Instagram, Twitter/X, Douyin, Bilibili, Vimeo...</strong>
            </p>

            {/* Input URL Bar */}
            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: 'var(--text-muted)' }}>
                Đường dẫn Video (Video URL)
              </label>
              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <div style={{ position: 'relative', flex: 1 }}>
                  <input 
                    type="text" 
                    placeholder="Dán đường dẫn video vào đây (ví dụ: https://www.youtube.com/watch?v=... hoặc TikTok/FB link)"
                    value={dlUrl}
                    onChange={e => setDlUrl(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter') handleFetchDlInfo(); }}
                    style={{ paddingRight: '40px', fontSize: '0.95rem' }}
                  />
                  {dlUrl && (
                    <button 
                      onClick={() => { setDlUrl(''); setDlInfo(null); setDownloadResult(null); }}
                      style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', background: 'transparent', color: 'var(--text-muted)', padding: '4px', fontSize: '0.9rem' }}
                      title="Xóa link"
                    >
                      ✖
                    </button>
                  )}
                </div>

                <button 
                  onClick={async () => {
                    try {
                      const text = await navigator.clipboard.readText();
                      if (text) {
                        setDlUrl(text);
                      }
                    } catch (err) {}
                  }}
                  style={{ background: 'rgba(255,255,255,0.08)', color: '#f8fafc', border: '1px solid var(--border-color)', whiteSpace: 'nowrap' }}
                  title="Dán từ Clipboard"
                >
                  📋 Dán
                </button>

                <button 
                  className="btn-primary" 
                  onClick={handleFetchDlInfo}
                  disabled={isFetchingInfo || !dlUrl.trim()}
                  style={{ whiteSpace: 'nowrap' }}
                >
                  {isFetchingInfo ? '⌛ Đang lấy info...' : '🔍 Lấy Thông Tin'}
                </button>
              </div>
            </div>

            {/* Video Info Preview Card */}
            {dlInfo && (
              <div style={{ 
                background: 'rgba(15, 23, 42, 0.8)', 
                border: '1px solid rgba(59, 130, 246, 0.4)', 
                borderRadius: '12px', 
                padding: '1.25rem', 
                marginBottom: '1.5rem',
                display: 'flex',
                gap: '1.25rem',
                alignItems: 'center',
                animation: 'fadeIn 0.3s ease-out'
              }}>
                {dlInfo.thumbnail ? (
                  <img 
                    src={dlInfo.thumbnail} 
                    alt="Thumbnail" 
                    style={{ width: '160px', height: '90px', objectFit: 'cover', borderRadius: '8px', border: '1px solid var(--border-color)', flexShrink: 0 }} 
                  />
                ) : (
                  <div style={{ width: '160px', height: '90px', background: 'rgba(0,0,0,0.4)', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.8rem', flexShrink: 0 }}>
                    🎬 No Preview
                  </div>
                )}

                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.4rem', flexWrap: 'wrap' }}>
                    <span style={{ background: 'rgba(59, 130, 246, 0.2)', color: '#38bdf8', padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: '600' }}>
                      🌐 {dlInfo.extractor}
                    </span>
                    <span style={{ background: 'rgba(16, 185, 129, 0.2)', color: '#10b981', padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: '600' }}>
                      ⏱️ {dlInfo.duration_formatted}
                    </span>
                  </div>

                  <h3 style={{ fontSize: '1.05rem', fontWeight: '600', color: '#f8fafc', marginBottom: '0.4rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={dlInfo.title}>
                    {dlInfo.title}
                  </h3>

                  <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                    👤 Tác giả / Kênh: <strong style={{ color: '#e2e8f0' }}>{dlInfo.uploader}</strong>
                  </p>
                </div>
              </div>
            )}

            {/* Quality Options & Action */}
            <div style={{ marginBottom: '1.5rem', background: 'rgba(0,0,0,0.2)', padding: '1.25rem', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
              <label style={{ display: 'block', marginBottom: '0.75rem', fontWeight: '600', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                🎯 Chọn Chất Lượng / Định Dạng Tải Về
              </label>

              <div className="option-group" style={{ marginBottom: '1.25rem' }}>
                <button 
                  className={`chip-btn ${dlFormat === 'best' ? 'selected' : ''}`}
                  onClick={() => setDlFormat('best')}
                >
                  ✨ Cao Nhất (Gốc Best HD/4K)
                </button>
                <button 
                  className={`chip-btn ${dlFormat === '1080p' ? 'selected' : ''}`}
                  onClick={() => setDlFormat('1080p')}
                >
                  📺 Full HD (1080p)
                </button>
                <button 
                  className={`chip-btn ${dlFormat === '720p' ? 'selected' : ''}`}
                  onClick={() => setDlFormat('720p')}
                >
                  📱 HD (720p)
                </button>
                <button 
                  className={`chip-btn ${dlFormat === '480p' ? 'selected' : ''}`}
                  onClick={() => setDlFormat('480p')}
                >
                  ⚡ SD (480p)
                </button>
                <button 
                  className={`chip-btn ${dlFormat === 'mp3' ? 'selected' : ''}`}
                  onClick={() => setDlFormat('mp3')}
                  style={{ borderColor: dlFormat === 'mp3' ? '#ec4899' : '', background: dlFormat === 'mp3' ? '#ec4899' : '' }}
                >
                  🎵 Chỉ Âm Thanh (MP3 Audio)
                </button>
              </div>

              <button 
                className="btn-primary" 
                style={{ width: '100%', padding: '14px', fontSize: '1.05rem', fontWeight: '600', background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)', boxShadow: '0 4px 14px rgba(16, 185, 129, 0.4)' }}
                onClick={handleStartDownload}
                disabled={isDownloading || !dlUrl.trim()}
              >
                {isDownloading ? '⏳ Đang Tải Video (Vui lòng chờ)...' : '📥 Tải Video Về Máy Server'}
              </button>
            </div>

            {/* Downloading Progress Indicator */}
            {isDownloading && (
              <div style={{ textAlign: 'center', padding: '1.5rem', background: 'rgba(16, 185, 129, 0.1)', border: '1px dashed #10b981', borderRadius: '12px', marginBottom: '1.5rem' }}>
                <div style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>🔄</div>
                <p style={{ color: '#10b981', fontWeight: '600', marginBottom: '0.25rem' }}>Hệ thống đang tiến hành nạp & xử lý dữ liệu video...</p>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{dlProgressMsg}</p>
              </div>
            )}

            {/* Download Result Panel */}
            {downloadResult && (
              <div style={{ background: 'rgba(16, 185, 129, 0.15)', border: '1px solid #10b981', borderRadius: '12px', padding: '1.5rem', animation: 'fadeIn 0.4s ease-out' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div>
                    <h3 style={{ color: '#10b981', fontWeight: '700', fontSize: '1.1rem', marginBottom: '0.25rem' }}>
                      🎉 Đã Tải Video Thành Công!
                    </h3>
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                      Kích thước file: <strong style={{ color: '#f8fafc' }}>{downloadResult.file_size}</strong> | Định dạng: <strong style={{ color: '#f8fafc' }}>{downloadResult.format_choice.toUpperCase()}</strong>
                    </p>
                  </div>

                  <a 
                    href={downloadResult.file_url} 
                    download={downloadResult.file_name}
                    target="_blank" 
                    rel="noreferrer"
                    style={{ background: '#10b981', color: 'white', padding: '10px 20px', borderRadius: '8px', textDecoration: 'none', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '0.5rem', boxShadow: '0 4px 14px rgba(16, 185, 129, 0.4)' }}
                  >
                    💾 Tải File Trực Tiếp Về PC
                  </a>
                </div>

                {downloadResult.format_choice === 'mp3' ? (
                  <audio controls autoPlay src={downloadResult.file_url} style={{ width: '100%', marginTop: '0.5rem' }}></audio>
                ) : (
                  <video controls src={downloadResult.file_url} style={{ width: '100%', maxHeight: '420px', borderRadius: '8px', border: '1px solid var(--border-color)', marginTop: '0.5rem' }}></video>
                )}
              </div>
            )}
          </div>

          {/* Download History Sidebar */}
          <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column' }}>
            <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem', color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              📜 Lịch sử tải video
            </h3>

            <div style={{ flex: 1, overflowY: 'auto' }}>
              {dlHistory.length === 0 ? (
                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  Chưa có video nào được tải trong phiên làm việc này.
                </p>
              ) : (
                dlHistory.map((item, idx) => (
                  <div key={idx} style={{ background: 'rgba(0,0,0,0.25)', padding: '0.85rem', borderRadius: '8px', marginBottom: '0.75rem', border: '1px solid var(--border-color)' }}>
                    <div style={{ fontWeight: '600', fontSize: '0.85rem', color: '#f8fafc', marginBottom: '4px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={item.title}>
                      {item.title}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '8px', display: 'flex', justifyContent: 'space-between' }}>
                      <span>📦 {item.file_size}</span>
                      <span>🎯 {item.format_choice}</span>
                    </div>
                    <a 
                      href={item.file_url} 
                      download={item.file_name} 
                      target="_blank" 
                      rel="noreferrer"
                      style={{ display: 'inline-block', width: '100%', textAlign: 'center', background: 'rgba(59, 130, 246, 0.2)', color: '#38bdf8', padding: '6px', borderRadius: '6px', textDecoration: 'none', fontSize: '0.8rem', fontWeight: '500' }}
                    >
                      ⬇️ Tải xuống ({item.file_name.split('.').pop()})
                    </a>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
