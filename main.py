from music21 import converter, instrument, note, chord
import librosa
import numpy as np
from mido import MidiFile, MidiTrack, MetaMessage, Message

input = librosa.example('./music/Onra_-_The_Anthem_62447208.mp3')
output_mid = './music'
notes = []

def audio_to_midi(input, output_mid, bpm=120, hop_length=512, fmin='C2', fmax='C7'):
    """
    input : str         – path to the input file
    output_mid: str     – path to save MIDI
    bpm : int           – bit in minute for MIDI
    hop_length : int    – analysis step (the smaller it is, the higher the time resolution)
    fmin, fmax : str    – notes' range
    """
    # download audio
    y, sr = librosa.load(input, sr=None)
    
    # find tone's height for each frame
    fmin_hz = librosa.note_to_hz(fmin)
    fmax_hz = librosa.note_to_hz(fmax)
    pitches, magnitudes = librosa.pyin(y, fmin=fmin_hz, fmax=fmax_hz, sr=sr, hop_length=hop_length)
    
    # changing sriped values (NaN) to 0 (silence)
    pitches = np.nan_to_num(pitches, nan=0.0)
    magnitudes = np.nan_to_num(magnitudes, nan=0.0)
    
    # Converting frequencies to MIDI-numbers
    midi_notes = librosa.hz_to_midi(pitches)
    midi_notes = np.round(midi_notes).astype(int)
    midi_notes[midi_notes < 0] = 0   # 0 means "no note"
    
    # timestamps for each frame 
    times = librosa.frames_to_time(np.arange(len(midi_notes)), sr=sr, hop_length=hop_length)
    
    # cominig frames with the same notes
    segments = []
    current_note = None
    start_idx = 0
    
    for i, note in enumerate(midi_notes):
        if note == 0:  # silence
            if current_note is not None:
                # finish current sigment
                end_idx = i - 1
                if end_idx >= start_idx:
                    segments.append({
                        'note': current_note,
                        'start': times[start_idx],
                        'end': times[end_idx] + (times[1] - times[0]) / 2,
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
                # if note changed finish previous sigment
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
    # final sigment
    if current_note is not None and start_idx < len(midi_notes):
        end_idx = len(midi_notes) - 1
        segments.append({
            'note': current_note,
            'start': times[start_idx],
            'end': times[end_idx] + (times[1] - times[0]) / 2,
            'velocity': np.mean(magnitudes[start_idx:end_idx+1])
        })
    
    # volume normalization
    if segments:
        max_vel = max(seg['velocity'] for seg in segments)
        if max_vel > 0:
            for seg in segments:
                vel = int((seg['velocity'] / max_vel) * 100) + 27
                seg['velocity'] = max(1, min(127, vel))
        else:
            for seg in segments:
                seg['velocity'] = 64
    else:
        print("No notes found. Check audiofile.")
        return
    
    # make MIDI-file
    mid = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    mid.tracks.append(track)
    
    # tempo
    tempo = MetaMessage('set_tempo', tempo=60000000 // bpm)
    track.append(tempo)

    ticks_per_sec = mid.ticks_per_beat * bpm / 60.0
    
    # genarate events note_on / note_off
    previous_ticks = 0
    for seg in segments:
        start_ticks = int(round(seg['start'] * ticks_per_sec))
        end_ticks   = int(round(seg['end'] * ticks_per_sec))
        
        delta_start = max(0, start_ticks - previous_ticks)
        track.append(Message('note_on', note=seg['note'], velocity=seg['velocity'], time=delta_start))
        
        duration_ticks = max(0, end_ticks - start_ticks)
        track.append(Message('note_off', note=seg['note'], velocity=0, time=duration_ticks))
        
        previous_ticks = end_ticks
    
    # saving
    mid.save(output_mid)
    print(f"MIDI was saved to {output_mid} (there are {len(segments)} notes in total)")

def makeNotes():
    notes = []
    file = "./music/output.mid"

    # get notes
    midi = converter.parse(file)
    parts = instrument.partitionByInstrument(midi)

    if parts:
        notes_to_parse = parts.parts[0].recurse()
    else:
        notes_to_parse = midi.flat.notes
    for element in notes_to_parse:
        if isinstance(element, note.Note):
            # add notes
            notes.append(str(element.pitch))
        elif isinstance(element, chord.Chord):
            # add chords
            notes.append('.'.join(str(n) for n in element.pitches))
    
    print(notes)

def main():
    audio_to_midi('input.wav', 'output.mid', bpm=120)
    makeNotes()

if __name__ == "__main__":
    audio_to_midi('input.wav', 'output.mid', bpm=120)
