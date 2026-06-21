from music21 import converter, instrument, note, chord

notes = []
file = "songs/my_song.mid"

# Получаем все ноты и аккорды из файла
midi = converter.parse(file)
parts = instrument.partitionByInstrument(midi)


if parts:
    notes_to_parse = parts.parts[0].recurse()
else:
    notes_to_parse = midi.flat.notes
for element in notes_to_parse:
    if isinstance(element, note.Note):
        # Добавляем "ноты, типа ля2-до3"
        notes.append(str(element.pitch))
    elif isinstance(element, chord.Chord):
        # Добавляем аккорды
        notes.append('.'.join(str(n) for n in element.pitches))

print(notes)


import librosa
import numpy as np
from mido import MidiFile, MidiTrack, MetaMessage, Message

input = librosa.example('./music/Onra_-_The_Anthem_62447208.mp3')

def audio_to_midi(input, output_mid, bpm=120, hop_length=512, fmin='C2', fmax='C7'):
    """
    input_wav : str     – путь к входному WAV-файлу
    output_mid: str     – путь для сохранения MIDI
    bpm        : int    – темп (ударов в минуту) для MIDI
    hop_length : int    – шаг анализа (чем меньше, тем выше временное разрешение)
    fmin, fmax : str    – диапазон нот (например, 'C2' ... 'C7')
    """
    # download audio
    y, sr = librosa.load(input, sr=None)
    
    # find tone's height for each frame
    fmin_hz = librosa.note_to_hz(fmin)
    fmax_hz = librosa.note_to_hz(fmax)
    pitches, magnitudes = librosa.pyin(y, fmin=fmin_hz, fmax=fmax_hz, sr=sr, hop_length=hop_length)
    
    # Замена пропущенных значений (NaN) на 0 (тишина)
    pitches = np.nan_to_num(pitches, nan=0.0)
    magnitudes = np.nan_to_num(magnitudes, nan=0.0)
    
    # 3. Преобразование частот в номера MIDI-нот (с округлением до целых)
    midi_notes = librosa.hz_to_midi(pitches)
    midi_notes = np.round(midi_notes).astype(int)
    midi_notes[midi_notes < 0] = 0   # 0 означает «нет ноты»
    
    # 4. Временные метки для каждого кадра (в секундах)
    times = librosa.frames_to_time(np.arange(len(midi_notes)), sr=sr, hop_length=hop_length)
    
    # 5. Сегментация: объединение последовательных кадров с одинаковой нотой
    segments = []
    current_note = None
    start_idx = 0
    
    for i, note in enumerate(midi_notes):
        if note == 0:  # тишина
            if current_note is not None:
                # завершаем текущий сегмент
                end_idx = i - 1
                if end_idx >= start_idx:
                    segments.append({
                        'note': current_note,
                        'start': times[start_idx],
                        'end': times[end_idx] + (times[1] - times[0]) / 2,  # полшага для компенсации
                        'velocity': np.mean(magnitudes[start_idx:end_idx+1])
                    })
                current_note = None
                start_idx = i + 1
            else:
                start_idx = i + 1
        else:
            if current_note is None:
                current_note = note
                start_idx = i
            elif note != current_note:
                # нота изменилась – закрываем предыдущий сегмент
                end_idx = i - 1
                if end_idx >= start_idx:
                    segments.append({
                        'note': current_note,
                        'start': times[start_idx],
                        'end': times[end_idx] + (times[1] - times[0]) / 2,
                        'velocity': np.mean(magnitudes[start_idx:end_idx+1])
                    })
                current_note = note
                start_idx = i
    # последний сегмент
    if current_note is not None and start_idx < len(midi_notes):
        end_idx = len(midi_notes) - 1
        segments.append({
            'note': current_note,
            'start': times[start_idx],
            'end': times[end_idx] + (times[1] - times[0]) / 2,
            'velocity': np.mean(magnitudes[start_idx:end_idx+1])
        })
    
    # 6. Нормализация громкости (velocity) в диапазон 1–127
    if segments:
        max_vel = max(seg['velocity'] for seg in segments)
        if max_vel > 0:
            for seg in segments:
                # линейная нормализация с небольшим смещением, чтобы избежать нуля
                vel = int((seg['velocity'] / max_vel) * 100) + 27
                seg['velocity'] = max(1, min(127, vel))
        else:
            for seg in segments:
                seg['velocity'] = 64
    else:
        print("Не обнаружено нот. Проверьте аудиофайл.")
        return
    
    # 7. Создание MIDI-файла
    mid = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    mid.tracks.append(track)
    
    # Задаём темп
    tempo = MetaMessage('set_tempo', tempo=60000000 // bpm)  # микросекунды на четверть
    track.append(tempo)
    
    # Количество тиков в секунду
    ticks_per_sec = mid.ticks_per_beat * bpm / 60.0
    
    # 8. Генерация событий note_on / note_off с правильными дельта-временами
    previous_ticks = 0
    for seg in segments:
        start_ticks = int(round(seg['start'] * ticks_per_sec))
        end_ticks   = int(round(seg['end'] * ticks_per_sec))
        
        # Дельта до начала ноты
        delta_start = max(0, start_ticks - previous_ticks)
        track.append(Message('note_on', note=seg['note'], velocity=seg['velocity'], time=delta_start))
        
        # Дельта до окончания ноты (длительность в тиках)
        duration_ticks = max(0, end_ticks - start_ticks)
        track.append(Message('note_off', note=seg['note'], velocity=0, time=duration_ticks))
        
        previous_ticks = end_ticks
    
    # 9. Сохранение
    mid.save(output_mid)
    print(f"MIDI сохранён в {output_mid} (всего {len(segments)} нот)")

# Пример использования
if __name__ == "__main__":
    audio_to_midi('input.wav', 'output.mid', bpm=120)
