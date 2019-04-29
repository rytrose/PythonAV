from magenta import music as mm
from magenta.models.music_vae import configs
from magenta.models.music_vae import TrainedModel

import numpy as np


class Variator:
    def __init__(self):
        self.config = configs.CONFIG_MAP["cat-mel_2bar_big"]
        self.config.data_converter.max_tensors_per_item = None

        print("Loading model...")
        self.model = TrainedModel(
            self.config,
            batch_size=8,
            checkpoint_dir_or_path="models/cat-mel_2bar_big.tar"
        )

    def latent_space_manipulator(self, mu):
        noise = np.random.uniform(low=0.0, high=0.5, size=(1, 512))
        noised_mu = mu + noise
        return noised_mu

    def make_variation(self, midi_data):
        input_sequence = mm.midi_to_note_sequence(midi_data)
        _, mu, _ = self.model.encode([input_sequence])
        altered_latent_vector = self.latent_space_manipulator(mu)
        results = self.model.decode(
            length=self.config.hparams.max_seq_len,
            z=altered_latent_vector,
            temperature=0.5
        )
        return mm.sequence_proto_to_pretty_midi(results[0])


if __name__ == '__main__':
    v = Variator()
