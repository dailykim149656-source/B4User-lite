# Data Notes

`personas_sample.jsonl` is a small handcrafted demo fixture for local b4user runs. It is not an export of `nvidia/Nemotron-Personas-Korea`.

To use Nemotron-Personas-Korea with B4User v0.1, use the importer:

```bash
b4user import-nemotron \
  --dataset nvidia/Nemotron-Personas-Korea \
  --split train \
  --n 5000 \
  --seed 42 \
  --output data/processed/nemotron_personas_5k.jsonl
```

The importer writes PersonaRecord-compatible JSONL with at least:

- `persona_id`: use the dataset `uuid` or another stable unique id
- `persona`: use the dataset `persona` field

Recommended optional mappings:

- `age` -> `age`
- `gender` -> `sex`
- `province` -> `province`
- `city` -> `district`
- `occupation` -> `occupation`
- `education` -> `education_level`

Additional Nemotron fields are preserved under `metadata.source_fields`.

B4User v0.1 intentionally does not download large remote datasets during demo runs. Keep raw and processed Nemotron data under `data/raw/` or `data/processed/`; both directories are ignored by Git.

Nemotron-Personas-Korea is listed on Hugging Face with a `cc-by-4.0` license. Preserve source and license attribution when sharing derived data.
