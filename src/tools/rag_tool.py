import re
import unicodedata

from src.config.settings import settings
from src.rag.embeddings import EmbeddingModel
from src.rag.preprocessors import clean_text
from src.rag.vector_db import ChromaVectorStore


class RAGTool:
    """
    Busca fragmentos relevantes en los apuntes del curso.

    Combina recuperacion semantica con busqueda lexical, vecinos y reranking
    simple segun la intencion de la pregunta.
    """

    TECHNICAL_TERMS = {
        "accuracy",
        "alexnet",
        "arquitectura",
        "arquitecturas",
        "auc",
        "autoencoder",
        "autoencoders",
        "backpropagation",
        "bce",
        "bert",
        "bpe",
        "cnn",
        "convolucional",
        "convolucionales",
        "coseno",
        "cross-entropy",
        "decoder",
        "denoising",
        "dense",
        "densenet",
        "embedding",
        "embeddings",
        "encoder",
        "f1",
        "f1-score",
        "googlenet",
        "hydra",
        "lenet",
        "llm",
        "llms",
        "mnist",
        "onnx",
        "precision",
        "recall",
        "relu",
        "resnet",
        "rag",
        "sigmoide",
        "softmax",
        "specaugment",
        "speech",
        "tanh",
        "tokenizacion",
        "tokenization",
        "u-net",
        "unet",
        "variacional",
        "variational",
        "vgg",
        "vgg16",
        "wordpiece",
    }

    TERM_EXPANSIONS = {
        "cnn": ["cnn", "convolucional", "convolucionales", "redes convolucionales"],
        "convolucional": ["cnn", "convolucional", "convolucionales"],
        "arquitecturas": ["arquitectura", "arquitecturas", "lenet", "alexnet", "vgg", "vgg16", "resnet", "googlenet"],
        "u-net": ["u-net", "unet", "u net", "biomedical", "segmentacion", "segmentacion biom"],
        "unet": ["u-net", "unet", "u net", "biomedical", "segmentacion"],
        "autoencoder": ["autoencoder", "autoencoders", "vanilla", "denoising", "variacional", "variational", "encoder", "decoder"],
        "autoencoders": ["autoencoder", "autoencoders", "vanilla", "denoising", "variacional", "variational", "encoder", "decoder"],
        "tokenizacion": ["tokenizacion", "tokenization", "token", "tokens", "wordpiece", "bpe", "byte", "subword", "palabra"],
        "tokenization": ["tokenizacion", "tokenization", "token", "tokens", "wordpiece", "bpe", "byte", "subword", "palabra"],
        "rag": ["rag", "retrieval", "augmented", "generation", "recuperacion", "aumentacion", "generacion", "retriever", "prompt"],
        "f1": ["f1", "f1-score", "fi-score", "precision", "recall"],
        "f1-score": ["f1", "f1-score", "fi-score", "precision", "recall"],
        "examen": ["examen", "examen final", "semana 18", "evaluaciones", "calendario"],
        "evaluacion": ["evaluacion", "evaluaciones", "quiz", "tarea", "proyecto", "examen", "calendario"],
        "evaluaciones": ["evaluacion", "evaluaciones", "quiz", "tarea", "proyecto", "examen", "calendario"],
        "quiz": ["quiz", "respuestasquiz", "respuestas quiz"],
        "hydra": ["hydra", "notebook", "notebooks", "archivos.py", ".py", "scripts"],
        "speech": ["speech commands", "specaugment", "onnx", "comandos de voz"],
        "specaugment": ["speech commands", "specaugment", "onnx", "comandos de voz"],
        "onnx": ["speech commands", "specaugment", "onnx", "onnx runtime"],
    }

    STOPWORDS = {
        "a",
        "al",
        "como",
        "con",
        "cual",
        "cuales",
        "cuando",
        "de",
        "del",
        "el",
        "en",
        "es",
        "esta",
        "estas",
        "este",
        "estos",
        "explica",
        "explique",
        "funciona",
        "hizo",
        "la",
        "las",
        "lo",
        "los",
        "menciona",
        "mencionan",
        "para",
        "por",
        "que",
        "quien",
        "se",
        "segun",
        "son",
        "su",
        "un",
        "una",
        "y",
    }

    def __init__(self):
        self.embedding_model = EmbeddingModel(settings.EMBEDDING_MODEL)
        self.vector_store = ChromaVectorStore(
            persist_dir=settings.VECTOR_DB_DIR,
            collection_name=settings.COLLECTION_NAME,
        )

    def search_notes(self, query: str, n_results: int = 5) -> list[dict]:
        if not query or not query.strip():
            raise ValueError("La consulta no puede estar vacia.")

        plan = self._build_query_plan(query, n_results)
        query_embedding = self.embedding_model.embed_query(query)
        semantic_results = self._semantic_search(query_embedding, plan["semantic_k"])
        all_chunks = self.vector_store.get_all_chunks()
        lexical_results = self._lexical_search(all_chunks, plan)
        neighbor_results = self._neighbor_chunks(all_chunks, [*semantic_results, *lexical_results], plan)
        cover_results = self._cover_chunks(all_chunks, [*semantic_results, *lexical_results], plan)
        merged = self._merge_results(
            lexical_results,
            semantic_results,
            neighbor_results,
            cover_results,
            limit=len(all_chunks),
        )
        scored = [
            (self._score_chunk(chunk, plan), chunk)
            for chunk in merged
        ]
        scored.sort(key=lambda item: item[0], reverse=True)

        return [
            chunk
            for score, chunk in scored
            if score > -100
        ][: plan["final_k"]]

    def _semantic_search(self, query_embedding: list[float], n_results: int) -> list[dict]:
        results = self.vector_store.search(
            query_embedding=query_embedding,
            n_results=n_results,
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        formatted_results = []

        for text, metadata, distance in zip(documents, metadatas, distances):
            formatted_results.append({
                "text": text,
                "metadata": metadata,
                "distance": distance,
            })

        return formatted_results

    def _build_query_plan(self, query: str, requested_results: int) -> dict:
        normalized_query = self._normalize(query)
        intent = self._classify_intent(normalized_query)
        weeks = self._extract_weeks(normalized_query)
        lexical_terms = self._extract_terms(normalized_query)

        if intent == "calendar_lookup":
            lexical_terms.extend([
                "calendario",
                "entrega",
                "evaluacion",
                "evaluaciones",
                "examen",
                "examen final",
                "fecha",
                "quiz",
                "semana 18",
                "tarea",
            ])

        final_k = max(requested_results, 15 if intent in {"topic_lookup", "calendar_lookup", "author_lookup"} else 8)
        semantic_k = max(final_k * 2, 30)

        return {
            "query": query,
            "normalized_query": normalized_query,
            "intent": intent,
            "weeks": weeks,
            "terms": self._unique_terms(lexical_terms),
            "final_k": final_k,
            "semantic_k": semantic_k,
        }

    def _classify_intent(self, normalized_query: str) -> str:
        author_signals = [
            "quien hizo",
            "quien escribio",
            "quien realizo",
            "autor",
            "autoria",
            "de quien son",
        ]
        topic_signals = [
            "arquitectura",
            "arquitecturas",
            "como funciona",
            "compara",
            "cual es la formula",
            "diferencia",
            "explica",
            "explique",
            "formula",
            "menciona",
            "mencionan",
            "que es",
            "tipos",
        ]
        calendar_signals = [
            "calendario",
            "cuando",
            "entrega",
            "evaluacion",
            "evaluaciones",
            "examen",
            "fecha",
            "quiz",
            "semana",
        ]

        if any(signal in normalized_query for signal in author_signals):
            return "author_lookup"

        has_author_action = any(
            term in normalized_query
            for term in ["hizo", "escribio", "realizo"]
        )
        has_author_object = any(
            term in normalized_query
            for term in ["apunte", "apuntes", "resumen"]
        )

        if has_author_action and has_author_object:
            return "author_lookup"

        if any(signal in normalized_query for signal in topic_signals):
            return "topic_lookup"

        if any(signal in normalized_query for signal in calendar_signals):
            return "calendar_lookup"

        return "topic_lookup"

    def _extract_weeks(self, normalized_query: str) -> list[int]:
        weeks = []

        for match in re.finditer(r"\bsemana\s+(\d+)\b", normalized_query):
            weeks.append(int(match.group(1)))

        return sorted(set(weeks))

    def _extract_terms(self, normalized_query: str) -> list[str]:
        terms = []
        tokens = re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)?", normalized_query)

        for token in tokens:
            if token in self.STOPWORDS or len(token) < 3:
                continue

            terms.append(token)

            if token in self.TECHNICAL_TERMS:
                terms.extend(self.TERM_EXPANSIONS.get(token, []))

        for term, expansions in self.TERM_EXPANSIONS.items():
            if term in normalized_query:
                terms.extend(expansions)

        return terms

    def _lexical_search(self, all_chunks: list[dict], plan: dict) -> list[dict]:
        results = []
        terms = plan["terms"]

        if not terms and not plan["weeks"]:
            return results

        for chunk in all_chunks:
            metadata = chunk.get("metadata", {})

            if not self._source_matches_week(metadata, plan):
                week_score = 0
            else:
                week_score = 1

            text = self._chunk_search_text(chunk)
            term_matches = sum(1 for term in terms if self._term_in_text(term, text))

            if term_matches or week_score:
                chunk_copy = chunk.copy()
                chunk_copy["lexical_matches"] = term_matches
                results.append(chunk_copy)

        return results

    def _neighbor_chunks(
        self,
        all_chunks: list[dict],
        base_chunks: list[dict],
        plan: dict,
    ) -> list[dict]:
        if plan["intent"] not in {"topic_lookup", "calendar_lookup"}:
            return []

        indexed = {}

        for chunk in all_chunks:
            metadata = chunk.get("metadata", {})
            key = metadata.get("source")

            if not key:
                continue

            indexed.setdefault(key, []).append(chunk)

        for chunks in indexed.values():
            chunks.sort(
                key=lambda item: (
                    self._safe_int(item.get("metadata", {}).get("page")),
                    self._safe_int(item.get("metadata", {}).get("chunk_index")),
                )
            )

        neighbors = []
        terms = plan["terms"]

        for chunk in base_chunks:
            if self._score_chunk(chunk, plan) < 2:
                continue

            metadata = chunk.get("metadata", {})
            source = metadata.get("source")

            if not source or source not in indexed:
                continue

            source_chunks = indexed[source]
            position = self._find_chunk_position(source_chunks, chunk)

            if position is None:
                continue

            for neighbor_position in [position - 1, position + 1]:
                if 0 <= neighbor_position < len(source_chunks):
                    neighbor = source_chunks[neighbor_position]
                    neighbor_text = self._chunk_search_text(neighbor)
                    neighbor_matches = sum(1 for term in terms if self._term_in_text(term, neighbor_text))

                    if neighbor_matches or plan["intent"] == "calendar_lookup":
                        neighbors.append(neighbor)

        return neighbors

    def _cover_chunks(
        self,
        all_chunks: list[dict],
        base_chunks: list[dict],
        plan: dict,
    ) -> list[dict]:
        if plan["intent"] != "author_lookup":
            return []

        matched_sources = {
            chunk.get("metadata", {}).get("source")
            for chunk in base_chunks
            if self._score_chunk(chunk, plan) >= 1
        }
        cover_chunks = []

        for chunk in all_chunks:
            metadata = chunk.get("metadata", {})

            if (
                metadata.get("source") in matched_sources
                and self._safe_int(metadata.get("page")) == 1
                and self._safe_int(metadata.get("chunk_index")) == 0
            ):
                cover_chunks.append(chunk)

        return cover_chunks

    def _score_chunk(self, chunk: dict, plan: dict) -> float:
        metadata = chunk.get("metadata", {})
        text = self._chunk_search_text(chunk)
        source = str(metadata.get("source", ""))
        distance = chunk.get("distance")
        score = 0.0

        for term in plan["terms"]:
            if self._term_in_text(term, text):
                score += 2.0 if term in self.TECHNICAL_TERMS or len(term) > 6 else 1.0

        if self._source_matches_week(metadata, plan):
            score += 5.0

        if plan["weeks"] and not self._source_matches_week(metadata, plan):
            score -= 3.0

        if metadata.get("topic") and self._normalize(str(metadata.get("topic"))) in plan["normalized_query"]:
            score += 1.5

        if distance is not None:
            score += max(0.0, 2.0 - float(distance))

        if self._is_cover_chunk(metadata) and plan["intent"] != "author_lookup":
            score -= 3.0

        cleaned_text = clean_text(chunk.get("text", ""))

        if len(cleaned_text) < 80:
            score -= 3.0

        if len(cleaned_text) < 20:
            score -= 10.0

        return score

    def _source_matches_week(self, metadata: dict, plan: dict) -> bool:
        if not plan["weeks"]:
            return False

        source = str(metadata.get("source", ""))
        week = self._safe_int(metadata.get("week"))

        return (
            week in plan["weeks"]
            or any(source.startswith(f"{target_week}_") for target_week in plan["weeks"])
        )

    def _is_cover_chunk(self, metadata: dict) -> bool:
        return (
            self._safe_int(metadata.get("page")) == 1
            and self._safe_int(metadata.get("chunk_index")) == 0
        )

    def _find_chunk_position(self, chunks: list[dict], target: dict) -> int | None:
        target_metadata = target.get("metadata", {})
        target_key = (
            target_metadata.get("source"),
            target_metadata.get("page"),
            target_metadata.get("chunk_index"),
        )

        for index, chunk in enumerate(chunks):
            metadata = chunk.get("metadata", {})
            key = (
                metadata.get("source"),
                metadata.get("page"),
                metadata.get("chunk_index"),
            )

            if key == target_key:
                return index

        return None

    def _chunk_search_text(self, chunk: dict) -> str:
        metadata = chunk.get("metadata", {})
        metadata_text = " ".join(str(value) for value in metadata.values())
        text = f"{chunk.get('text', '')} {metadata_text}"
        return self._normalize(text)

    def _term_in_text(self, term: str, text: str) -> bool:
        normalized_term = self._normalize(term)
        return normalized_term in text

    def _merge_results(self, *result_lists: list[dict], limit: int) -> list[dict]:
        merged = []
        seen = set()

        for result_list in result_lists:
            for result in result_list:
                metadata = result.get("metadata", {})
                key = (
                    metadata.get("source"),
                    metadata.get("page"),
                    metadata.get("chunk_index"),
                )

                if key in seen:
                    continue

                seen.add(key)
                merged.append(result)

                if len(merged) >= limit:
                    return merged

        return merged

    def _unique_terms(self, terms: list[str]) -> list[str]:
        unique = []
        seen = set()

        for term in terms:
            normalized_term = self._normalize(term)

            if not normalized_term or normalized_term in seen:
                continue

            seen.add(normalized_term)
            unique.append(normalized_term)

        return unique

    def _normalize(self, text: str) -> str:
        text = clean_text(text or "")
        text = unicodedata.normalize("NFKD", text)
        text = "".join(char for char in text if not unicodedata.combining(char))
        text = text.lower()
        text = text.replace("¿", " ").replace("?", " ")
        text = re.sub(r"[^a-z0-9.+#-]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _safe_int(self, value) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return -1
