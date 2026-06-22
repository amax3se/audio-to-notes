from music21 import converter, instrument, note, chord
from basic_pitch.inference import predict
from basic_pitch import ICASSP_2022_MODEL_PATH

def audio_to_midi(path, output_path):
    # converting
    model_output, midi_data, note_events = predict(path, ICASSP_2022_MODEL_PATH)

    # saving
    midi_data.write(output_path + "/your-song.mid")
    print(f"MIDI was saved to {output_path}/your-song.mid")

def makeNotes(output_path):
    notes = []
    mid_file = output_path + "/your-song.mid"

    # create notes
    midi = converter.parse(mid_file)
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

    # parse MIDI and convert to .xml
    score = converter.parse(mid_file)
    score.write('musicxml', fp=output_path+'/notes.xml', format='xml')

    print(f"Notes was saved to {output_path}/notes.xml")

def main():
    path = input('Enter path to your song: ')
    output_path = input('Enter path to output folder: ')

    audio_to_midi(path, output_path)
    makeNotes(output_path)

if __name__ == "__main__":
    main()
