from measurements.streaming_measurement import StreamingTempMeasurement


class BmeDallasSlowMeasurement(StreamingTempMeasurement):
    """
    Ukázkové druhé měření založené na JSON protokolu.

    Rozdíly oproti základnímu StreamingTempMeasurement:
      - Delší doba měření
      - Nižší vzorkovací frekvence

    Slouží jako šablona:
      - pro vlastní DURATION_S, SAMPLE_RATE_HZ
      - nebo pro pozdější rozšíření (např. jiné chování on_start/on_stop).
    """

    DURATION_S = 600.0      # měříme 60 sekund včetně 0
    SAMPLE_RATE_HZ = 0.5   # 1 vzorek za 2 sekundy
