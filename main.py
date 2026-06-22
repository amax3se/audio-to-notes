from music21 import converter, instrument, note, chord
from basic_pitch.inference import predict
from basic_pitch import ICASSP_2022_MODEL_PATH

# path to the song 
input = './music/Onra_-_The_Anthem_62447208.mp3'

def audio_to_midi(input):
    # converting
    model_output, midi_data, note_events = predict(input, ICASSP_2022_MODEL_PATH)

    # saving
    midi_data.write("./music/output.mid")
    print(f"MIDI was saved to ~/music/output.mid")

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

    # parse MIDI and convert to .xml
    score = converter.parse(file)
    score.write('musicxml', fp='./music/notes.xml', format='xml')

def main():
    audio_to_midi(input)
    makeNotes()

if __name__ == "__main__":
    main()
