from faster_whisper import WhisperModel
import json
import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox, scrolledtext
import time
import string # Ensure string is imported
import re
from thefuzz import fuzz
import threading
import functools
from queue import Queue
import gc  # Garbage collection for memory management

try:
    import torch
    TORCH_AVAILABLE = True
    CUDA_AVAILABLE = torch.cuda.is_available()
except ImportError:
    TORCH_AVAILABLE = False
    CUDA_AVAILABLE = False

class WhisperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Faster Whisper Arayüzü")
        self.root.geometry("650x700")
        self.root.resizable(True, True)
        
        # Değişkenler
        self.audio_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.srt_path = tk.StringVar() # For optional SRT file input
        self.model_size = tk.StringVar(value="medium")  # Türkçe için medium daha iyi
        self.selected_device = tk.StringVar() # For CPU/GPU selection
        
        # Gelişmiş ayarlar için değişkenler
        self.language = tk.StringVar(value="tr")  # Türkçe varsayılan
        self.compute_type = tk.StringVar(value="int8")
        self.beam_size = tk.IntVar(value=5)
        self.vad_filter = tk.BooleanVar(value=False) # VAD filtresi varsayılan olarak kapalı
        self.vad_threshold = tk.DoubleVar(value=0.0) # VAD eşiği varsayılan olarak 0.0
        self.temperature = tk.DoubleVar(value=0.0)
        self.initial_prompt = tk.StringVar(value="")
        self.word_timestamps = tk.BooleanVar(value=True)
        
        # Eşik değerleri için değişkenler (Düzeltme Aracı)
        self.primary_threshold_var = tk.DoubleVar(value=70.0)
        self.context_threshold_var = tk.DoubleVar(value=85.0)
        self.key_relaxed_threshold_var = tk.DoubleVar(value=40.0)
        
        # Notebook oluştur (sekmeler için)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Ana ayarlar sekmesi
        main_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(main_frame, text="Ana Ayarlar")
        
        # Gelişmiş ayarlar sekmesi
        advanced_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(advanced_frame, text="Gelişmiş Ayarlar")
        
        # Yardım sekmesi
        help_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(help_frame, text="Yardım ve Bilgi")
        
        # Düzeltme Aracı sekmesi
        self.correction_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.correction_frame, text="Düzeltme Aracı")
        
        # Ana ayarlar sekmesini doldur
        ttk.Label(main_frame, text="Ses Dosyası:").grid(column=0, row=0, sticky="w", pady=5)
        ttk.Entry(main_frame, width=50, textvariable=self.audio_path).grid(column=0, row=1, sticky="ew")
        ttk.Button(main_frame, text="Dosya Seç", command=self.select_audio).grid(column=1, row=1, padx=5)
        
        # İlerleme çubuğu ve yüzde etiketi ekle
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_percent = tk.StringVar(value="0%")
        
        self.progress_frame = ttk.Frame(main_frame)
        self.progress_frame.grid(column=0, row=16, columnspan=2, sticky="ew", pady=5)
        self.progress_frame.grid_remove()  # Başlangıçta gizli
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, orient="horizontal", 
                                          length=100, mode="determinate", 
                                          variable=self.progress_var)
        self.progress_bar.pack(fill="x", expand=True, side="left")
        
        self.percent_label = ttk.Label(self.progress_frame, textvariable=self.progress_percent, width=5)
        self.percent_label.pack(side="right", padx=5)
        
        ttk.Label(main_frame, text="Çıktı Dosyası:").grid(column=0, row=2, sticky="w", pady=5)
        ttk.Entry(main_frame, width=50, textvariable=self.output_path).grid(column=0, row=3, sticky="ew")
        ttk.Button(main_frame, text="Konum Seç", command=self.select_output).grid(column=1, row=3, padx=5)
        
        # SRT Dosyası Seçimi (İsteğe Bağlı)
        ttk.Label(main_frame, text="SRT Dosyası (İsteğe Bağlı - Metin İyileştirme İçin):").grid(column=0, row=4, sticky="w", pady=5)
        ttk.Entry(main_frame, width=50, textvariable=self.srt_path).grid(column=0, row=5, sticky="ew")
        ttk.Button(main_frame, text="SRT Seç", command=self.select_srt).grid(column=1, row=5, padx=5)
        
        ttk.Label(main_frame, text="Model Büyüklüğü:").grid(column=0, row=6, sticky="w", pady=5)
        model_combo = ttk.Combobox(main_frame, textvariable=self.model_size)
        model_combo['values'] = ("tiny", "base", "small", "medium", "large", "large-v2")
        model_combo.grid(column=0, row=7, sticky="ew")
        model_combo.current(3)  # Medium varsayılan (Türkçe için daha iyi)
        ttk.Label(main_frame, text="(Türkçe için medium veya large önerilir)").grid(column=0, row=8, sticky="w", pady=(0,5))
        
        ttk.Label(main_frame, text="Dil:").grid(column=0, row=9, sticky="w", pady=5)
        language_combo = ttk.Combobox(main_frame, textvariable=self.language)
        language_combo['values'] = ("tr", "auto", "en", "de", "fr", "es", "it")
        language_combo.grid(column=0, row=10, sticky="ew")
        language_combo.current(0)  # Türkçe varsayılan
        
        ttk.Label(main_frame, text="İşlem Birimi:").grid(column=0, row=11, sticky="w", pady=5)
        self.device_combobox = ttk.Combobox(main_frame, textvariable=self.selected_device, state="readonly")
        self.device_combobox.grid(column=0, row=12, sticky="ew")
        
        ttk.Separator(main_frame, orient="horizontal").grid(column=0, row=13, columnspan=2, sticky="ew", pady=15)
        
        # Tam metin ipucu (prompt) alanı
        ttk.Label(main_frame, text="Tam Metin (Doğruluğu Arttırır):").grid(column=0, row=14, sticky="w", pady=5)
        ttk.Label(main_frame, text="Ses kaydının tam metnini biliyorsanız, buraya yapıştırın:").grid(column=0, row=15, sticky="w", pady=(0,5))
        self.full_text_prompt = scrolledtext.ScrolledText(main_frame, width=50, height=6, wrap=tk.WORD)
        self.full_text_prompt.grid(column=0, row=16, columnspan=2, sticky="ew", pady=5)
        
        # İşlem butonu
        ttk.Button(main_frame, text="Transkripsiyon Başlat", command=self.run_transcription).grid(column=0, row=17, columnspan=2, pady=20)
        
        # Durum göstergesi
        self.status = tk.StringVar(value="Hazır")
        ttk.Label(main_frame, textvariable=self.status).grid(column=0, row=18, columnspan=2)
        
        # İşlemci Kullanım Bilgisi
        self.device_info_label = ttk.Label(main_frame, text="Kullanılan İşlemci: CPU (değiştirilemez)")
        self.device_info_label.grid(column=0, row=19, columnspan=2, sticky="w", pady=(5,0))
        
        # Gelişmiş ayarlar sekmesini doldur
        ttk.Label(advanced_frame, text="Compute Type:").grid(column=0, row=0, sticky="w", pady=5)
        compute_combo = ttk.Combobox(advanced_frame, textvariable=self.compute_type)
        compute_combo['values'] = ("int8", "int8_float16", "float16", "float32")
        compute_combo.grid(column=1, row=0, sticky="ew", padx=10)
        ttk.Label(advanced_frame, text="(Hesaplama tipi - int8 daha hızlı, float16/32 daha doğru)").grid(column=0, row=1, columnspan=2, sticky="w", pady=(0,5))
        
        ttk.Label(advanced_frame, text="Beam Size:").grid(column=0, row=2, sticky="w", pady=5)
        beam_spin = ttk.Spinbox(advanced_frame, from_=1, to=10, textvariable=self.beam_size)
        beam_spin.grid(column=1, row=2, sticky="ew", padx=10)
        ttk.Label(advanced_frame, text="(Daha yüksek değer daha doğru sonuç verir ancak yavaşlatır)").grid(column=0, row=3, columnspan=2, sticky="w", pady=(0,5))
        
        ttk.Label(advanced_frame, text="VAD Filtresi:").grid(column=0, row=4, sticky="w", pady=5)
        ttk.Checkbutton(advanced_frame, variable=self.vad_filter).grid(column=1, row=4, sticky="w", padx=10)
        ttk.Label(advanced_frame, text="(Sessiz bölümleri filtreler, konuşma tanımayı iyileştirir)").grid(column=0, row=5, columnspan=2, sticky="w", pady=(0,5))
        
        ttk.Label(advanced_frame, text="VAD Eşiği:").grid(column=0, row=6, sticky="w", pady=5)
        vad_scale_frame = ttk.Frame(advanced_frame) # Frame for scale and label
        vad_scale_frame.grid(column=1, row=6, sticky="ew", padx=10)
        vad_scale = ttk.Scale(vad_scale_frame, from_=0.0, to=0.9, orient="horizontal", variable=self.vad_threshold, command=self._update_vad_label)
        vad_scale.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.vad_value_label = ttk.Label(vad_scale_frame, text=f"{self.vad_threshold.get():.1f}")
        self.vad_value_label.pack(side=tk.LEFT, padx=(5,0))
        ttk.Label(advanced_frame, text="(Daha düşük değer daha fazla sesi algılar, yüksek değer daha seçicidir)").grid(column=0, row=7, columnspan=2, sticky="w", pady=(0,5))
        
        ttk.Label(advanced_frame, text="Temperature:").grid(column=0, row=8, sticky="w", pady=5)
        temp_scale_frame = ttk.Frame(advanced_frame) # Frame for scale and label
        temp_scale_frame.grid(column=1, row=8, sticky="ew", padx=10)
        temp_scale = ttk.Scale(temp_scale_frame, from_=0.0, to=1.0, orient="horizontal", variable=self.temperature, command=self._update_temp_label)
        temp_scale.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.temp_value_label = ttk.Label(temp_scale_frame, text=f"{self.temperature.get():.1f}")
        self.temp_value_label.pack(side=tk.LEFT, padx=(5,0))
        ttk.Label(advanced_frame, text="(0: en olası sonuç, yüksek değer: daha yaratıcı sonuçlar)").grid(column=0, row=9, columnspan=2, sticky="w", pady=(0,5))
        
        ttk.Label(advanced_frame, text="İlk İpucu Metni:").grid(column=0, row=10, sticky="w", pady=5)
        ttk.Entry(advanced_frame, width=40, textvariable=self.initial_prompt).grid(column=1, row=10, sticky="ew", padx=10)
        ttk.Label(advanced_frame, text="(Modele başlangıç ipucu, 'Bu bir Türkçe konuşma kaydıdır' gibi)").grid(column=0, row=11, columnspan=2, sticky="w", pady=(0,5))
        
        ttk.Label(advanced_frame, text="Kelime Zamanlamaları:").grid(column=0, row=12, sticky="w", pady=5)
        ttk.Checkbutton(advanced_frame, variable=self.word_timestamps).grid(column=1, row=12, sticky="w", padx=10)
        ttk.Label(advanced_frame, text="(Her kelime için ayrı zaman bilgisi, kapalıysa cümle zamanları)").grid(column=0, row=13, columnspan=2, sticky="w", pady=(0,5))
        
        # Türkçe için öneriler
        ttk.Separator(advanced_frame, orient="horizontal").grid(column=0, row=14, columnspan=2, sticky="ew", pady=15)
        ttk.Label(advanced_frame, text="Türkçe İçin Önerilen Ayarlar", font=("", 10, "bold")).grid(column=0, row=15, columnspan=2, sticky="w", pady=5)
        ttk.Label(advanced_frame, text="- Medium veya Large model kullanın").grid(column=0, row=16, columnspan=2, sticky="w", pady=2)
        ttk.Label(advanced_frame, text="- VAD filtresi açık olmalı").grid(column=0, row=17, columnspan=2, sticky="w", pady=2)
        ttk.Label(advanced_frame, text="- Beam Size 5 ideal").grid(column=0, row=18, columnspan=2, sticky="w", pady=2)
        
        # Varsayılan ayarları yükle butonu
        ttk.Button(advanced_frame, text="Türkçe İçin Varsayılanları Yükle", command=self.load_turkish_defaults).grid(column=0, row=19, columnspan=2, pady=20)
        
        # Yardım sekmesi içeriği
        help_content = """
WHISPER MODELİ AYARLARI HAKKINDA BİLGİLENDİRME

1. MODEL BÜYÜKLÜĞÜ
   - tiny: En küçük model, hızlı ama daha az doğru
   - base: Küçük, dengeli model
   - small: Orta büyüklükte, dengeli
   - medium: Türkçe için iyi, doğruluk/hız dengeli
   - large/large-v2: En büyük, en doğru ama yavaş model

2. COMPUTE TYPE
   - int8: En hızlı, hafıza dostu ama daha az hassas
   - float16/32: Daha doğru ama daha fazla hafıza kullanır ve yavaştır

3. BEAM SIZE
   - Değer arttıkça, model farklı olasılıkları daha fazla değerlendirir
   - Türkçe için 5 genelde iyi sonuç verir
   - Yüksek değerler işlemi yavaşlatır

4. VAD FİLTRESİ (Voice Activity Detection)
   - Ses kaydında sadece konuşma olan kısımları işler
   - Sessiz bölümleri atlar, gürültüyü azaltır
   - Türkçe için açık olması önerilir

5. TEMPERATURE
   - 0.0: En olası sonuçları seçer (en doğru)
   - Yükseldikçe: Modelin çeşitliliği artar, yaratıcılığı artar
   - Gerçek konuşma kayıtları için düşük tutun

6. TAM METİN KULLANIMI
   - Ses kaydının tam metnini biliyorsanız, yazın
   - Model bu metni referans alarak kelimeleri doğru eşleştirir
   - Zamanlama doğruluğunu önemli ölçüde artırır

7. KELİME ZAMANLAMALARI
   - Açık: Her kelime için başlangıç/bitiş zamanı
   - Kapalı: Cümle/segment başına tek zaman

8. İLK İPUCU METNİ
   - Modele başlangıç için verilen metin ipucu
   - Örnek: "Bu bir Türkçe ders anlatımıdır"
   - İçerik türünü belirtmek doğruluğu artırır

BU PROGRAM HAKKINDA
Bu program, Faster Whisper modelini kullanarak ses dosyalarını yazıya 
dönüştürür ve kelimelerin zaman damgalarını çıkarır. Özellikle
Türkçe ses kayıtları için optimize edilmiştir.
        """
        
        help_text = scrolledtext.ScrolledText(help_frame, width=60, height=30, wrap=tk.WORD)
        help_text.pack(fill="both", expand=True, padx=5, pady=5)
        help_text.insert(tk.END, help_content)
        help_text.config(state="disabled")  # Salt okunur
        
        # Sütun ve satır ağırlıklarını ayarla
        main_frame.columnconfigure(0, weight=1)
        advanced_frame.columnconfigure(1, weight=1)
        self.correction_frame.columnconfigure(0, weight=1) # Correction frame column weight
        self.correction_frame.columnconfigure(2, weight=0) # Button column

        self._create_correction_tab_widgets() # Call method to populate the new tab
        self._initialize_device_selection() # Initialize device options
        self._update_vad_label() # Initial update for VAD label
        self._update_temp_label() # Initial update for Temperature label
    
    def _initialize_device_selection(self):
        devices = ["CPU"]
        initial_status = "Hazır"
        default_device = "CPU"

        if TORCH_AVAILABLE and CUDA_AVAILABLE:
            devices.append("GPU (CUDA)")
            initial_status = "Hazır (CUDA Kullanılabilir)"
            default_device = "GPU (CUDA)" # Default to GPU if available
        elif not TORCH_AVAILABLE:
            initial_status = "Hazır (PyTorch kurulu değil, sadece CPU kullanılabilir)"
        elif not CUDA_AVAILABLE:
            initial_status = "Hazır (CUDA bulunamadı, sadece CPU kullanılabilir)"

        self.device_combobox['values'] = devices
        self.selected_device.set(default_device)
        self.status.set(initial_status)

    def _update_vad_label(self, event=None):
        self.vad_value_label.config(text=f"{self.vad_threshold.get():.1f}")

    def _update_temp_label(self, event=None):
        self.temp_value_label.config(text=f"{self.temperature.get():.1f}")
    
    def _create_correction_tab_widgets(self):
        """Düzeltme Aracı sekmesinin içeriğini oluşturur."""
        # JSON Dosyası
        ttk.Label(self.correction_frame, text="JSON Dosyası (Düzeltilecek):").grid(column=0, row=0, sticky="w", pady=(5,0), columnspan=2)
        self.correction_json_path = tk.StringVar()
        ttk.Entry(self.correction_frame, width=50, textvariable=self.correction_json_path).grid(column=0, row=1, sticky="ew", columnspan=1, padx=(0,5))
        ttk.Button(self.correction_frame, text="JSON Seç", command=self._select_correction_json).grid(column=1, row=1, padx=5, sticky="w")

        # Referans TXT Dosyası
        ttk.Label(self.correction_frame, text="Referans TXT Dosyası (Karşılaştırma için):").grid(column=0, row=2, sticky="w", pady=(10,0), columnspan=2)
        self.correction_txt_path = tk.StringVar()
        ttk.Entry(self.correction_frame, width=50, textvariable=self.correction_txt_path).grid(column=0, row=3, sticky="ew", columnspan=1, padx=(0,5))
        ttk.Button(self.correction_frame, text="TXT Seç", command=self._select_correction_txt).grid(column=1, row=3, padx=5, sticky="w")

        # Kontrol Butonları
        control_buttons_frame = ttk.Frame(self.correction_frame)
        control_buttons_frame.grid(column=0, row=4, columnspan=2, pady=10, sticky="ew")
        
        ttk.Button(control_buttons_frame, text="Dosyaları Yükle ve Görüntüle", command=self._start_correction_with_thresholds).pack(side=tk.LEFT, padx=(0,10))
        ttk.Button(control_buttons_frame, text="Düzeltilmiş JSON'u Kaydet", command=self._save_corrected_json).pack(side=tk.LEFT)

        # Eşik Değerleri Ayar Bölümü
        threshold_settings_frame = ttk.LabelFrame(self.correction_frame, text="Eşik Değerleri (%)", padding="10")
        threshold_settings_frame.grid(row=5, column=0, columnspan=2, pady=(0, 10), sticky="ew")

        # Primary Threshold
        ttk.Label(threshold_settings_frame, text="3/3 Eşleşme (Ana):").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        primary_scale = ttk.Scale(threshold_settings_frame, from_=0, to=100, orient=tk.HORIZONTAL, variable=self.primary_threshold_var, length=150,
                                  command=lambda v: self.primary_threshold_val_label.config(text=f"{float(v):.0f}%"))
        primary_scale.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        self.primary_threshold_val_label = ttk.Label(threshold_settings_frame, text=f"{self.primary_threshold_var.get():.0f}%")
        self.primary_threshold_val_label.grid(row=0, column=2, sticky="w", padx=5, pady=2)

        # Context Threshold
        ttk.Label(threshold_settings_frame, text="P/N Bağlam (2.5 Eşl.):").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        context_scale = ttk.Scale(threshold_settings_frame, from_=0, to=100, orient=tk.HORIZONTAL, variable=self.context_threshold_var, length=150,
                                  command=lambda v: self.context_threshold_val_label.config(text=f"{float(v):.0f}%"))
        context_scale.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        self.context_threshold_val_label = ttk.Label(threshold_settings_frame, text=f"{self.context_threshold_var.get():.0f}%")
        self.context_threshold_val_label.grid(row=1, column=2, sticky="w", padx=5, pady=2)

        # Key Relaxed Threshold
        ttk.Label(threshold_settings_frame, text="Anahtar K. Esnek (2.5 Eşl.):").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        key_relaxed_scale = ttk.Scale(threshold_settings_frame, from_=0, to=100, orient=tk.HORIZONTAL, variable=self.key_relaxed_threshold_var, length=150,
                                      command=lambda v: self.key_relaxed_threshold_val_label.config(text=f"{float(v):.0f}%"))
        key_relaxed_scale.grid(row=2, column=1, sticky="ew", padx=5, pady=2)
        self.key_relaxed_threshold_val_label = ttk.Label(threshold_settings_frame, text=f"{self.key_relaxed_threshold_var.get():.0f}%")
        self.key_relaxed_threshold_val_label.grid(row=2, column=2, sticky="w", padx=5, pady=2)

        # Text Display Areas
        display_frame = ttk.LabelFrame(self.correction_frame, text="Dosya İçerikleri", padding="10")
        display_frame.grid(row=6, column=0, columnspan=2, pady=10, sticky="nsew")
        
        display_frame.columnconfigure(0, weight=1)
        display_frame.columnconfigure(1, weight=1)
        display_frame.rowconfigure(1, weight=1) 

        ttk.Label(display_frame, text="Referans TXT İçeriği:").grid(row=0, column=0, sticky="w", padx=5, pady=(5,0))
        self.txt_correction_display_area = scrolledtext.ScrolledText(display_frame, wrap=tk.WORD, height=15)
        self.txt_correction_display_area.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        ttk.Label(display_frame, text="JSON İçeriği (Düzeltilecek):").grid(row=0, column=1, sticky="w", padx=5, pady=(5,0))
        self.json_correction_display_area = scrolledtext.ScrolledText(display_frame, wrap=tk.WORD, height=15)
        self.json_correction_display_area.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)

        self.correction_frame.rowconfigure(6, weight=1) 
        self.correction_frame.columnconfigure(0, weight=1)

    def _clean_for_compare(self, text):
        """Metin karşılaştırması için metni temizler ve standartlaştırır.
        
        Args:
            text (str): Temizlenecek metin
            
        Returns:
            str: Noktalama ve özel karakterlerden arındırılmış metin
        """
        # None kontrolü ekle
        if not text:
            return ""
            
        # Turkish-specific character handling for lowercase
        text_lower = str(text).replace('İ', 'i').replace('I', 'ı').lower()

        # Characters to remove using Unicode escape sequences for reliability
        bullet_circle = "\u25cf"      # ●
        bullet_triangle = "\u25ba"    # ►
        bullet_dot = "\u2022"         # •
        left_double_quote = "\u201c"  # “
        right_double_quote = "\u201d" # ”
        left_single_quote = "\u2018"  # ‘
        right_single_quote = "\u2019" # ’ 
        ellipsis = "\u2026"     # …
        en_dash = "\u2013"       # –
        em_dash = "\u2014"       # —

        punctuation_to_remove_explicitly = (
            bullet_circle + bullet_triangle + bullet_dot +
            left_double_quote + right_double_quote +
            left_single_quote + right_single_quote +
            ellipsis + en_dash + em_dash
        )
        
        # Tüm noktalama işaretlerini tek adımda birleştir ve tekrarları kaldır
        all_punctuation = string.punctuation + punctuation_to_remove_explicitly
        unique_chars = ''.join(set(all_punctuation))  # set ile benzersiz karakterleri al
        
        # Tek adımda noktalama işaretlerini kaldır (daha verimli)
        translator = str.maketrans('', '', unique_chars)
        text_no_punct = text_lower.translate(translator)
        
        # Boşlukları standartlaştır - tek bir boşluk bırak
        return " ".join(text_no_punct.split())

    def _start_correction_with_thresholds(self):
        primary_thresh = int(self.primary_threshold_var.get())
        context_thresh = int(self.context_threshold_var.get())
        key_relaxed_thresh = int(self.key_relaxed_threshold_var.get())
        self._load_files_for_correction(primary_thresh, context_thresh, key_relaxed_thresh)

    def _load_files_for_correction(self, primary_threshold, context_threshold, key_relaxed_threshold):
        json_path_str = self.correction_json_path.get()
        txt_path_str = self.correction_txt_path.get()

        if not json_path_str or not txt_path_str:
            messagebox.showerror("Hata", "Lütfen hem JSON hem de TXT dosyalarını seçin.")
            return

        try:
            with open(json_path_str, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
                if isinstance(loaded_data, list):
                    self.current_correction_data = [{k: v for k, v in item.items()} if isinstance(item, dict) else item for item in loaded_data]
                else:
                    self.current_correction_data = loaded_data 
            with open(txt_path_str, 'r', encoding='utf-8') as f:
                self.txt_content_lines_for_correction = [str(line) for line in f.read().splitlines()]

            self.update_status_correction(f"Dosyalar yüklendi: JSON: {len(self.current_correction_data)} öğe, TXT: {len(self.txt_content_lines_for_correction)} satır")

            bullet_chars_to_detect = ['●', '•', '►'] # İsteğiniz üzerine sadece bu üçü
            txt_contexts = []
            unmatched_txt_log_messages = [] # Eşleşmeyen TXT log mesajları için (gerekirse daha sonra kullanılır)

            # İşlem durum bilgisini güncelle
            self.update_status_correction("TXT işleniyor: Bağlam oluşturuluyor...")

            for current_line_idx, raw_current_line in enumerate(self.txt_content_lines_for_correction):
                stripped_current_line = raw_current_line.lstrip()
                
                bullet_char_found_for_line = None
                text_after_bullet_on_line = ""

                for bc_candidate in bullet_chars_to_detect:
                    if stripped_current_line.startswith(bc_candidate):
                        bullet_char_found_for_line = bc_candidate
                        text_after_bullet_on_line = stripped_current_line[len(bc_candidate):].lstrip()
                        break
                
                if bullet_char_found_for_line and text_after_bullet_on_line:
                    words_after_bullet_original = text_after_bullet_on_line.split()
                    
                    if not words_after_bullet_original:
                        continue

                    original_key_text = words_after_bullet_original[0]
                    key_word = self._clean_for_compare(original_key_text)
                    key_word_base = None
                    if "'" in original_key_text or "\u2019" in original_key_text: # Standart ve tipografik kesme işareti kontrolü
                        base_part = original_key_text.split("'", 1)[0].split("\u2019", 1)[0]
                        key_word_base = self._clean_for_compare(base_part)
                    
                    prev_cleaned_word = "<NONE>"
                    strip_offset = raw_current_line.find(stripped_current_line)
                    text_before_bullet_char_on_current_line = raw_current_line[:strip_offset].strip()
                    if text_before_bullet_char_on_current_line:
                        words_before_bullet_cleaned = [self._clean_for_compare(w) for w in text_before_bullet_char_on_current_line.split() if self._clean_for_compare(w)]
                        if words_before_bullet_cleaned:
                            prev_cleaned_word = words_before_bullet_cleaned[-1]
                    
                    if prev_cleaned_word == "<NONE>":
                        for prev_line_search_idx in range(current_line_idx - 1, -1, -1):
                            prev_raw_line_content = self.txt_content_lines_for_correction[prev_line_search_idx]
                            prev_line_words_cleaned = [self._clean_for_compare(w) for w in prev_raw_line_content.strip().split() if self._clean_for_compare(w)]
                            if prev_line_words_cleaned:
                                prev_cleaned_word = prev_line_words_cleaned[-1]
                                break
                    
                    next_cleaned_word = "<NONE>"
                    if len(words_after_bullet_original) > 1:
                        next_word_on_same_line_original = words_after_bullet_original[1]
                        cleaned_candidate = self._clean_for_compare(next_word_on_same_line_original)
                        if cleaned_candidate:
                            next_cleaned_word = cleaned_candidate
                    
                    if next_cleaned_word == "<NONE>":
                        for next_line_search_idx in range(current_line_idx + 1, len(self.txt_content_lines_for_correction)):
                            next_raw_line_content = self.txt_content_lines_for_correction[next_line_search_idx]
                            next_line_words_cleaned = [self._clean_for_compare(w) for w in next_raw_line_content.strip().split() if self._clean_for_compare(w)]
                            if next_line_words_cleaned:
                                next_cleaned_word = next_line_words_cleaned[0]
                                break
                    
                    context_info = {
                        "bullet": bullet_char_found_for_line,
                        "prev": prev_cleaned_word,
                        "key": key_word,
                        "key_base": key_word_base,
                        "next": next_cleaned_word,
                        "txt_line_index": current_line_idx,
                        "txt_raw_line": raw_current_line,
                        "original_word": original_key_text, 
                        "used": False
                    }
                    txt_contexts.append(context_info)
                    # print(f"  TXT Bağlamı Eklendi (Satır {current_line_idx}, Kelime '{key_original}'): Madde: {bullet_char_found_for_line} P:'{prev_cleaned_word}' K:'{key_cleaned}' N:'{next_cleaned_word}' -- Ham: '{raw_current_line}'")

            # Durum bilgisini güncelle ve boş bağlam kontrolü
            self.update_status_correction(f"Toplam {len(txt_contexts)} adet TXT madde başı bağlamı oluşturuldu")

            if not txt_contexts: 
                messagebox.showinfo("Bilgi", f"TXT dosyasında '{', '.join(repr(b) for b in bullet_chars_to_detect)}' ile başlayan ve işlenebilir bağlam içeren kelime bulunamadı. Değişiklik yapılmayacak.")
                self.update_correction_text_display()
                self.update_status_correction("TXT'de uygun madde başı bulunamadı.")
                return

            # JSON işleme durum bilgisini güncelle
            self.update_status_correction(f"JSON öğeleri işleniyor: Madde işaretleri eşleştiriliyor (Eşik değerleri: {primary_threshold}%/{context_threshold}%/{key_relaxed_threshold}%)...")
            # Eşikleri parametre olarak aldık, burada tanımlamaya gerek yok.
            updated_count = 0
            
            for txt_idx, txt_context in enumerate(txt_contexts):
                if txt_context["used"]:
                    continue

                txt_bullet = txt_context["bullet"]
                txt_prev_cleaned = txt_context["prev"]
                txt_key_cleaned = txt_context["key"] # Full form
                txt_key_base_cleaned = txt_context.get("key_base") # Base form, might be None
                txt_next_cleaned = txt_context["next"]

                found_match_for_this_txt_context = False

                for json_i in range(len(self.current_correction_data)):
                    json_item_dict = self.current_correction_data[json_i]
                    if not isinstance(json_item_dict, dict) or 'text' not in json_item_dict:
                        continue

                    original_json_text = str(json_item_dict.get('text', ''))
                    
                    if not original_json_text.strip() or \
                       any(original_json_text.lstrip().startswith(b_char) for b_char in bullet_chars_to_detect):
                        continue

                    json_key_words = original_json_text.strip().split() # Önce boşlukları temizle, sonra kelimelere ayır
                    first_json_key_word = json_key_words[0] if json_key_words else "" # Eğer kelime varsa ilkini al
                    # Hata ayıklama mesajları kaldırıldı
                    cleaned_json_key_text = self._clean_for_compare(first_json_key_word)

                    if not cleaned_json_key_text:
                        # print(f"DEBUG: JSON Key Text empty after clean. Original: '{original_json_text}', First word extracted: '{first_json_key_word}'")
                        continue
                    
                    cleaned_json_prev_word = "<NONE>"
                    if json_i > 0:
                        prev_json_item_dict = self.current_correction_data[json_i-1]
                        if isinstance(prev_json_item_dict, dict) and 'text' in prev_json_item_dict:
                            prev_json_text = str(prev_json_item_dict.get('text','')).strip()
                            if prev_json_text and not any(prev_json_text.lstrip().startswith(b_char) for b_char in bullet_chars_to_detect):
                                prev_json_words = prev_json_text.split()
                                if prev_json_words:
                                    print(f"DEBUG PreClean JSON Prev: '{prev_json_words[-1]}' (JSON Index {json_i-1})")
                                    cleaned_json_prev_word = self._clean_for_compare(prev_json_words[-1])

                    cleaned_json_next_word = "<NONE>"
                    if (json_i + 1) < len(self.current_correction_data):
                        next_json_item_dict = self.current_correction_data[json_i+1]
                        if isinstance(next_json_item_dict, dict) and 'text' in next_json_item_dict:
                            next_json_text = str(next_json_item_dict.get('text','')).strip()
                            if next_json_text:
                                next_json_words = next_json_text.split()
                                if next_json_words:
                                     print(f"DEBUG PreClean JSON Next: '{next_json_words[0]}' (JSON Index {json_i+1})")
                                     cleaned_json_next_word = self._clean_for_compare(next_json_words[0])

                    # Tam eşleşme mantığı
                    # For prev_match (fuzzy, for primary and context thresholds)
                    prev_score = fuzz.ratio(txt_prev_cleaned, cleaned_json_prev_word)
                    prev_match_primary = (prev_score >= primary_threshold)
                    prev_match_context = (prev_score >= context_threshold)
                    print(f"DEBUG Match: Prev TXT:'{txt_prev_cleaned}' vs JSON:'{cleaned_json_prev_word}', Score: {prev_score} (P:{prev_match_primary}/{primary_threshold}, Ctx:{prev_match_context}/{context_threshold})")

                    # For key_match (fuzzy, trying full/base for primary and relaxed thresholds)
                    score_full_primary = fuzz.ratio(txt_key_cleaned, cleaned_json_key_text)
                    match_full_primary = (score_full_primary >= primary_threshold)
                    score_full_relaxed = fuzz.ratio(txt_key_cleaned, cleaned_json_key_text)
                    match_full_relaxed = (score_full_relaxed >= key_relaxed_threshold)

                    key_match_primary = match_full_primary
                    key_match_relaxed = match_full_relaxed
                    key_details_p = f"Full_P: '{txt_key_cleaned}' ({score_full_primary}/{primary_threshold})={match_full_primary}"
                    key_details_r = f"Full_R: '{txt_key_cleaned}' ({score_full_relaxed}/{key_relaxed_threshold})={match_full_relaxed}"

                    if txt_key_base_cleaned:
                        score_base_primary = fuzz.ratio(txt_key_base_cleaned, cleaned_json_key_text)
                        match_base_primary = (score_base_primary >= primary_threshold)
                        score_base_relaxed = fuzz.ratio(txt_key_base_cleaned, cleaned_json_key_text)
                        match_base_relaxed = (score_base_relaxed >= key_relaxed_threshold)
                        
                        key_match_primary = match_full_primary or match_base_primary
                        key_match_relaxed = match_full_relaxed or match_base_relaxed
                        key_details_p += f", Base_P: '{txt_key_base_cleaned}' ({score_base_primary}/{primary_threshold})={match_base_primary} -> KeyP_Match: {key_match_primary}"
                        key_details_r += f", Base_R: '{txt_key_base_cleaned}' ({score_base_relaxed}/{key_relaxed_threshold})={match_base_relaxed} -> KeyR_Match: {key_match_relaxed}"
                    else:
                        key_details_p += f" -> KeyP_Match: {key_match_primary}"
                        key_details_r += f" -> KeyR_Match: {key_match_relaxed}"

                    print(f"DEBUG Match: Key JSON:'{cleaned_json_key_text}' vs TXT_P ({key_details_p}) | TXT_R ({key_details_r})")

                    # For next_match (fuzzy, for primary and context thresholds)
                    next_score = fuzz.ratio(txt_next_cleaned, cleaned_json_next_word)
                    next_match_primary = (next_score >= primary_threshold)
                    next_match_context = (next_score >= context_threshold)
                    print(f"DEBUG Match: Next TXT:'{txt_next_cleaned}' vs JSON:'{cleaned_json_next_word}', Score: {next_score} (P:{next_match_primary}/{primary_threshold}, Ctx:{next_match_context}/{context_threshold})")

                    match_3_of_3 = (prev_match_primary and key_match_primary and next_match_primary)
                    match_2_point_5 = (prev_match_context and next_match_context and key_match_relaxed)

                    if match_3_of_3 or match_2_point_5:
                        item_to_update = self.current_correction_data[json_i]
                        
                        # Eşleşme, original_json_text'in ilk kelimesi üzerinden yapıldı.
                        # Bu ilk kelimeyi alıp formatlayacağız.
                        json_first_word = original_json_text.split(' ')[0] # original_json_text zaten str
                        
                        # TXT'den gelen orijinal madde işaretini al
                        original_txt_bullet = txt_context["bullet"]
                        
                        # Kullanılacak madde işaretini belirle (• ise ● yap, değilse orijinali kullan)
                        bullet_to_use_in_json = "●" if original_txt_bullet == "•" else original_txt_bullet
                        
                        # JSON öğesinin "text" alanını formatla ve güncelle
                        # JSON dosyasında literal '\n' olması için '\\n' kullan.
                        new_item_text_formatted = f"\\n{bullet_to_use_in_json} {json_first_word}"
                        item_to_update['text'] = new_item_text_formatted
                        
                        updated_count += 1
                        txt_context["used"] = True
                        found_match_for_this_txt_context = True
                        
                        print(f"    EYLEM: Metin FORMATLANDI ve GÜNCELLENDİ. JSON Index {json_i}. TXT Satır: {txt_context['txt_line_index']}.")
                        print(f"           Eski JSON: '{original_json_text}' -> Yeni JSON: {item_to_update['text']!r}")
                        print(f"           Eşleşen TXT Bağlamı: P:'{txt_prev_cleaned}' K:'{txt_key_cleaned}' N:'{txt_next_cleaned}'")
                        break 
                
                if not found_match_for_this_txt_context:
                    log_entry = f"- TXT Satırı {txt_context['txt_line_index']} ({txt_context['bullet']} P:'{txt_context['prev']}' K:'{txt_context['key']}' N:'{txt_context['next']}') için JSON'da tam eşleşme bulunamadı."
                    unmatched_txt_log_messages.append(log_entry)

            print(f"\\n----- İşlem Tamamlandı (Strateji v7) -----")
            self.update_correction_text_display()

            if unmatched_txt_log_messages:
                log_file_path = os.path.join(os.getcwd(), "unmatched_items_log.txt")
                try:
                    with open(log_file_path, 'w', encoding='utf-8') as f_log:
                        f_log.write("Aşağıdaki TXT satırları için JSON'da tam bağlamsal eşleşme bulunamadı ve bu nedenle formatlanmadı:\n\n")
                        for log_entry in unmatched_txt_log_messages:
                            f_log.write(log_entry + "\n")
                    info_message = f"{len(unmatched_txt_log_messages)} adet eşleşmeyen TXT satırı bulundu.\nDetaylar şu dosyaya yazıldı: {log_file_path}"
                    messagebox.showinfo("Eşleşmeyen Öğeler Loglandı", info_message)
                except Exception as e_log:
                    messagebox.showerror("Log Yazma Hatası", f"Eşleşmeyen öğeler log dosyasına yazılamadı: {e_log}")
            
            status_message = f"{updated_count} JSON öğesi, TXT bağlamlarına göre güncellendi."
            if updated_count == 0 and any(not tc["used"] for tc in txt_contexts):
                 status_message = "Bazı TXT madde işaretli bağlamları için JSON'da eşleşme bulunamadı."
            elif updated_count == 0 and not txt_contexts:
                 status_message = "İşlenecek TXT bağlamı bulunamadı."
            elif updated_count == 0:
                 status_message = "İşlenecek TXT bağlamları JSON ile eşleşmedi."

            self.update_status_correction(status_message)
            print(status_message)
            messagebox.showinfo("Bilgi", status_message)

        except FileNotFoundError:
            messagebox.showerror("Hata", "Belirtilen JSON veya TXT dosyası bulunamadı.")
            self.update_status_correction("Hata: Dosya bulunamadı.")
            print("Hata: Dosya bulunamadı.")
        except json.JSONDecodeError:
            messagebox.showerror("Hata", "JSON dosyası geçerli formatta değil.")
            self.update_status_correction("Hata: JSON formatı bozuk.")
            print("Hata: JSON formatı bozuk.")
        except Exception as e:
            self.update_status_correction(f"İşleme hatası: {str(e)}")
            print(f"Beklenmedik bir hata oluştu _load_files_for_correction: {type(e).__name__} - {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Kritik Hata", f"Dosyalar işlenirken beklenmedik bir hata oluştu: {str(e)}\\nDetaylar konsola yazdırıldı.")
            print(f"İşleme hatası: {e}")
            import traceback
            print(traceback.format_exc())

    def update_correction_text_display(self):
        """Düzeltme Aracı sekmesindeki JSON ve TXT metin alanlarını günceller."""
        # JSON metin alanını güncelle
        self.json_correction_display_area.config(state="normal")
        self.json_correction_display_area.delete("1.0", tk.END)
        if self.current_correction_data:
            for item in self.current_correction_data:
                self.json_correction_display_area.insert(tk.END, str(item.get('text', '')) + '\n')
        # self.json_correction_display_area.config(state="disabled") # Kullanıcı düzenleyebilmeli

        # TXT metin alanını güncelle
        self.txt_correction_display_area.config(state="normal")
        self.txt_correction_display_area.delete("1.0", tk.END)
        if hasattr(self, 'txt_content_lines_for_correction') and self.txt_content_lines_for_correction:
            for line in self.txt_content_lines_for_correction:
                self.txt_correction_display_area.insert(tk.END, str(line) + '\n')
        self.txt_correction_display_area.config(state="disabled") # TXT salt okunur kalmalı

    def update_status_correction(self, message: str):
        """Düzeltme Aracı için durum mesajını ayarlar (ana durum etiketini kullanır)."""
        self.status.set(message) # Ana durum etiketini kullan

    def _save_corrected_json(self):
        if not self.current_correction_data:
            messagebox.showwarning("Veri Yok", "Önce JSON verisini yükleyin ve düzenleyin.")
            return

        edited_lines = self.json_correction_display_area.get("1.0", tk.END).strip().split('\n')
        
        if len(edited_lines) != len(self.current_correction_data):
            # Kullanıcı satır eklemiş veya silmişse, bu basit güncelleme yöntemi sorun yaratabilir.
            # Şimdilik sadece uyaralım. Daha gelişmiş bir eşleştirme gerekebilir.
            if messagebox.askyesno("Satır Sayısı Uyuşmazlığı", 
                                   f"Düzenlenen metin satır sayısı ({len(edited_lines)}) ile orijinal JSON öğe sayısı ({len(self.current_correction_data)}) farklı.\\n"
                                   "Bu durum, özellikle satır sildiyseniz veya eklediyseniz, verilerin yanlış eşleşmesine neden olabilir.\\n"
                                   "Devam etmek istiyor musunuz? (İlk {min(len(edited_lines), len(self.current_correction_data))} öğe güncellenecek)"):
                pass # Kullanıcı devam etmek istiyor
            else:
                return # Kullanıcı iptal etti

        updated_count = 0
        min_len = min(len(edited_lines), len(self.current_correction_data))

        for i in range(min_len):
            if isinstance(self.current_correction_data[i], dict) and 'text' in self.current_correction_data[i]:
                self.current_correction_data[i]['text'] = edited_lines[i]
                updated_count +=1
            else:
                # Beklenmedik format durumunu log yerine duruma yansıt
                self.update_status_correction(f"Uyarı: Kayıt sırasında {i}. indeksteki JSON öğesi beklenmedik formatta, atlanıyor.")


        save_path = filedialog.asksaveasfilename(
            title="Düzeltilmiş JSON Dosyasını Kaydet",
            defaultextension=".json",
            filetypes=[("JSON Dosyaları", "*.json")],
            initialfile=self.correction_json_path.get() # Orijinal dosya adını öner
        )

        if not save_path:
            return # Kullanıcı iptal etti

        try:
            # Fix: Düzelt metinlerdeki çift-kaçışlı yeni satır karakterlerini (\\n -> \n)
            for item in self.current_correction_data:
                if isinstance(item, dict) and 'text' in item and isinstance(item['text'], str):
                    # Eğer text içinde "\n" varsa "\n"'e çevir
                    if '\\n' in item['text']:
                        item['text'] = item['text'].replace('\\n', '\n')
        
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(self.current_correction_data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Başarılı", f"{updated_count} öğe güncellenerek düzeltilmiş JSON dosyası kaydedildi: {save_path}")
        except Exception as e:
            messagebox.showerror("Kayıt Hatası", f"JSON dosyası kaydedilirken hata oluştu: {str(e)}")


    def _select_correction_json(self):
        file_path = filedialog.askopenfilename(
            title="Düzeltilecek JSON Dosyasını Seç",
            filetypes=[("JSON Dosyaları", "*.json")]
        )
        if file_path:
            self.correction_json_path.set(file_path)
            # Otomatik olarak output_path'i de set etmeyi düşünebiliriz
            # self.output_path.set(file_path) 

    def _select_correction_txt(self):
        file_path = filedialog.askopenfilename(
            title="Referans TXT Dosyasını Seç",
            filetypes=[("Metin Dosyaları", "*.txt")]
        )
        if file_path:
            self.correction_txt_path.set(file_path)

    def load_turkish_defaults(self):
        """Türkçe için en iyi ayarları yükler."""
        self.model_size.set("medium")
        self.language.set("tr")
        self.compute_type.set("int8")
        self.beam_size.set(5)
        self.vad_filter.set(True)
        self.vad_threshold.set(0.5)
        self.temperature.set(0.0)
        self.initial_prompt.set("Bu bir Türkçe konuşma kaydıdır.")
        self.word_timestamps.set(True)
        messagebox.showinfo("Bilgi", "Türkçe için önerilen ayarlar yüklendi.")
        self._update_vad_label() # Update label after loading defaults
        self._update_temp_label() # Update label after loading defaults
    
    def select_audio(self):
        file_path = filedialog.askopenfilename(
            title="Ses Dosyası Seç",
            filetypes=[("Ses Dosyaları", "*.wav;*.mp3;*.m4a;*.ogg;*.flac")]
        )
        if file_path:
            self.audio_path.set(file_path)
            # Varsayılan olarak aynı dizinde çıktı oluştur
            filename = os.path.splitext(os.path.basename(file_path))[0]
            default_output = os.path.join(os.path.dirname(file_path), f"{filename}_zamanlar.json")
            self.output_path.set(default_output)
    
    def select_output(self):
        file_path = filedialog.asksaveasfilename(
            title="Çıktı Dosyasını Kaydet",
            defaultextension=".json",
            filetypes=[("JSON Dosyaları", "*.json")]
        )
        if file_path:
            self.output_path.set(file_path)
    
    def select_srt(self):
        file_path = filedialog.askopenfilename(
            title="SRT Dosyası Seç",
            filetypes=[("SRT Dosyaları", "*.srt")]
        )
        if file_path:
            self.srt_path.set(file_path)        

    def parse_srt_for_text(self, srt_file_path):
        """SRT dosyasından metin içeriğini çıkarır ve birleştirir.
        Args:
            srt_file_path (str): SRT dosyasının tam yolu
        Returns:
            str or None: Birleştirilmiş metin içeriği veya hata durumunda None
        """
        if not srt_file_path or not os.path.exists(srt_file_path):
            messagebox.showwarning("SRT Dosya Hatası", "SRT dosyası bulunamadı veya geçersiz.")
            return None
            
        try:
            with open(srt_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if not content.strip():
                return None
                
            # Daha verimli bir şekilde SRT bloklarını işle
            blocks = content.strip().split('\n\n')
            # List comprehension ile doğrudan metin içeriklerini al
            all_text = [" ".join(block.split('\n')[2:]).strip() 
                       for block in blocks 
                       if len(block.split('\n')) >= 3]
                       
            # Boş olmayan metinleri tek bir string'de birleştir
            return " ".join(all_text) if all_text else None
            
        except UnicodeDecodeError:
            # UTF-8 ile okunamazsa diğer yaygın kodlamaları dene
            try:
                with open(srt_file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                    
                blocks = content.strip().split('\n\n')
                all_text = [" ".join(block.split('\n')[2:]).strip() 
                           for block in blocks 
                           if len(block.split('\n')) >= 3]
                           
                return " ".join(all_text) if all_text else None
                
            except Exception as e:
                messagebox.showwarning("SRT Kodlama Hatası", f"SRT dosyası farklı kodlama ile denenirken hata: {str(e)}")
                return None
        except Exception as e:
            messagebox.showwarning("SRT Okuma Hatası", f"SRT dosyası işlenirken hata: {str(e)}")
            return None
    
    def run_transcription(self):
        """Ses dosyasının transkripsiyonunu arka planda çalışan bir iş parçacığında başlatır.
        İlerleme bilgisini gösteren bir ilerleme çubuğu sunar ve kullanıcı arayüzünün donmasını engeller.
        """
        # Gerekli alanları kontrol et
        if not self.audio_path.get():
            messagebox.showerror("Hata", "Lütfen bir ses dosyası seçin.")
            return
        
        if not self.output_path.get():
            messagebox.showerror("Hata", "Lütfen çıktı dosyası konumunu seçin.")
            return
        
        # Cihaz seçimini optimize et
        chosen_device_display_name = self.selected_device.get()
        # Varsayılan olarak CPU kullan, gerektiğinde GPU'ya geç
        actual_device_to_use = "cuda" if (chosen_device_display_name == "GPU (CUDA)" and 
                                          TORCH_AVAILABLE and CUDA_AVAILABLE) else "cpu"
        
        # GPU seçildi ama kullanılamıyorsa uyarı göster
        if chosen_device_display_name == "GPU (CUDA)" and actual_device_to_use == "cpu":
            if not TORCH_AVAILABLE:
                messagebox.showwarning("GPU Hatası", "PyTorch kütüphanesi bulunamadığından GPU kullanılamıyor. CPU ile devam edilecek.")
            elif not CUDA_AVAILABLE:
                messagebox.showwarning("GPU Hatası", "CUDA uyumlu GPU bulunamadığından veya sürücülerde sorun olduğundan GPU kullanılamıyor. CPU ile devam edilecek.")

        # İşlem için gerekli parametreleri hazırla
        params = {
            'model_size': self.model_size.get(),
            'device': actual_device_to_use,
            'compute_type': self.compute_type.get(),
            'audio_path': self.audio_path.get(),
            'output_path': self.output_path.get(),
            'beam_size': self.beam_size.get(),
            'language': None if self.language.get() == "auto" else self.language.get(),
            'temperature': self.temperature.get(),
            'word_timestamps': self.word_timestamps.get(),
            'vad_filter': self.vad_filter.get(),
            'vad_threshold': self.vad_threshold.get() if self.vad_filter.get() else None
        }
        
        # İpucu metni ayarlarını belirle
        full_text_from_main_tab = self.full_text_prompt.get("1.0", tk.END).strip()
        srt_file_path_str = self.srt_path.get().strip()
        specific_initial_prompt = self.initial_prompt.get().strip()
        
        # İpucu metnini hazırla
        if full_text_from_main_tab:
            params['initial_prompt'] = full_text_from_main_tab
            self.status.set("Sağlanan TXT metni ipucu olarak kullanılıyor...")
        elif srt_file_path_str:
            parsed_srt_text = self.parse_srt_for_text(srt_file_path_str)
            if parsed_srt_text:
                lines = [line.strip() for line in parsed_srt_text.splitlines() if line.strip()]
                # Regex desenini önceden tanımla
                bullet_pattern = r'^\s*(?:●|•|►)\s*'
                processed_lines = [f"● {re.sub(bullet_pattern, '', line)}" for line in lines]
                params['initial_prompt'] = "\n".join(processed_lines) if processed_lines else ""
                self.status.set("SRT metni referans olarak kullanılıyor...")
            elif specific_initial_prompt:
                params['initial_prompt'] = specific_initial_prompt
                self.status.set("İlk ipucu metni kullanılıyor (SRT okunamadı)...")
        elif specific_initial_prompt:
            params['initial_prompt'] = specific_initial_prompt
            self.status.set("İlk ipucu metni kullanılıyor...")
        else:
            params['initial_prompt'] = None
            self.status.set("İpucu metni kullanılmıyor...")

        # İlerleme çubuğunu göster ve sıfırla
        self.progress_var.set(0)
        self.progress_percent.set("0%")
        self.progress_frame.grid()
        self.root.update()
        
        # İlerleme bilgisini taşıyacak kuyruk
        progress_queue = Queue()
        
        # Sonucu taşıyacak obje
        result = {'success': False, 'data': None, 'error': None, 'time': 0}
        
        # Arka planda çalışacak işlev
        def transcribe_task():
            try:
                start_time = time.time()
                
                # Model yükleme ilerleme bildirimi
                progress_queue.put(('status', f"Model yükleniyor ({params['device'].upper()})..."))
                progress_queue.put(('progress', 5))
                
                # Model yükle
                model = WhisperModel(params['model_size'], device=params['device'], 
                                    compute_type=params['compute_type'])
                
                # Transkripsiyon hazırlık bildirimi
                progress_queue.put(('status', f"Transkripsiyon için hazırlanıyor ({params['device'].upper()})..."))
                progress_queue.put(('progress', 10))
                
                # Transkripsiyonu başlat (callback ile ilerleme güncellemesi yap)
                segments, info = model.transcribe(
                    params['audio_path'],
                    beam_size=params['beam_size'],
                    language=params['language'],
                    temperature=params['temperature'],
                    initial_prompt=params['initial_prompt'],
                    word_timestamps=params['word_timestamps'],
                    vad_filter=params['vad_filter'],
                    vad_parameters={"threshold": params['vad_threshold']} if params['vad_filter'] else None
                )
                
                # Transkripsiyon tamamlandı, sonuçları işle
                progress_queue.put(('status', "Sonuçlar işleniyor ve kaydediliyor..."))
                progress_queue.put(('progress', 80))
                
                # Sonuçları topla
                word_timings = []
                use_word_timestamps = params['word_timestamps']
                
                # Bellekte yer açmak için paylaşımlı segment listesi oluştur
                segment_list = list(segments)
                
                # Segmentleri işle
                for segment in segment_list:
                    if use_word_timestamps:
                        # Her kelime için ayrı zaman bilgisi ekle
                        word_timings.extend([
                            {
                                "text": str(word.word).strip(),
                                "start": round(word.start, 2),
                                "end": round(word.end, 2)
                            } for word in segment.words
                        ])
                    else:
                        # Segment bazında zaman bilgisi ekle
                        word_timings.append({
                            "text": str(segment.text).strip(),
                            "start": round(segment.start, 2),
                            "end": round(segment.end, 2)
                        })
                
                # JSON dosyasına kaydet
                with open(params['output_path'], "w", encoding="utf-8") as f:
                    json.dump(word_timings, f, ensure_ascii=False, indent=2)
                
                end_time = time.time()
                transcription_time = round(end_time - start_time, 2)
                
                # Başarılı sonuç ayarla
                result['success'] = True
                result['data'] = {
                    'word_count': len(word_timings),
                    'device': params['device']
                }
                result['time'] = transcription_time
                
                # Tamamlama bildirimi
                progress_queue.put(('progress', 100))
                progress_queue.put(('status', f"Tamamlandı! ({params['device'].upper()}) Süre: {transcription_time} saniye."))
                
                # Bellek temizliği
                del model, segments, word_timings
                gc.collect()
                
            except Exception as e:
                result['success'] = False
                result['error'] = str(e)
                progress_queue.put(('status', f"Hata oluştu: {str(e)}"))
        
        # Ana iş parçacığı oluştur ve başlat
        thread = threading.Thread(target=transcribe_task)
        thread.daemon = True
        thread.start()
        
        # İlerleme kontrol döngüsü
        def check_progress():
            try:
                # Kuyrukta ilerleme bilgisi var mı kontrol et
                while not progress_queue.empty():
                    msg_type, msg_data = progress_queue.get()
                    
                    if msg_type == 'progress':
                        self.progress_var.set(msg_data)
                        self.progress_percent.set(f"{int(msg_data)}%")
                    elif msg_type == 'status':
                        self.status.set(msg_data)
                
                # İş parçacığı hala çalışıyor mu kontrol et
                if thread.is_alive():
                    # 100ms sonra tekrar kontrol et
                    self.root.after(100, check_progress)
                else:
                    # İşlem tamamlandı, ilerleme çubuğunu gizle
                    self.progress_frame.grid_remove()
                    
                    # Sonuçları göster
                    if result['success']:
                        device_used = result['data']['device'].upper()
                        word_count = result['data']['word_count']
                        process_time = result['time']
                        
                        completion_message = f"Tamamlandı! ({device_used}) Süre: {process_time} saniye. {word_count} kelime işlendi."
                        self.status.set(completion_message)
                        messagebox.showinfo("Başarılı", 
                                           f"Transkripsiyon ({device_used}) {process_time} saniyede tamamlandı.\n"
                                           f"Toplam {word_count} kelime işlendi ve sonuçlar kaydedildi:\n"
                                           f"{params['output_path']}")
                    else:
                        self.status.set(f"Hata oluştu: {result['error']}")
                        messagebox.showerror("Hata", f"İşlem sırasında bir hata oluştu:\n{result['error']}")
            except Exception as e:
                self.status.set(f"Beklenmeyen hata: {str(e)}")
                self.progress_frame.grid_remove()
        
        # İlerleme kontrolünü başlat
        check_progress()


if __name__ == "__main__":
    root = tk.Tk()
    app = WhisperGUI(root)
    root.mainloop()
