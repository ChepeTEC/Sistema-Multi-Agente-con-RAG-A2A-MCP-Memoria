import type { Citation, RagConfig } from "@/lib/types";

const base: Omit<Citation, "excerpt" | "score">[] = [
  {
    id: "src-1",
    author: "Carlos Mendoza",
    file: "apuntes-ml-carlos.pdf",
    date: "2024-09-12",
  },
  {
    id: "src-2",
    author: "Goodfellow, Bengio & Courville",
    file: "deep-learning-book-cap4.pdf",
    date: "2016-11-18",
  },
  {
    id: "src-3",
    author: "Andrew Ng",
    file: "cs229-lecture-notes.pdf",
    date: "2022-03-04",
  },
];

const excerpts: Record<RagConfig, string[]> = {
  fija: [
    "El descenso del gradiente es un algoritmo de optimización iterativo de primer orden que ajusta los parámetros del modelo en dirección opuesta al gradiente de la función de pérdida, escalado por una tasa de aprendizaje α.",
    "Formalmente, θ_{t+1} = θ_t − α · ∇L(θ_t). La elección de α condiciona la convergencia: valores grandes oscilan, valores pequeños convergen lento.",
    "En la práctica se usan variantes como SGD con momentum, RMSProp y Adam, que adaptan el paso por parámetro y suavizan la dirección de actualización.",
  ],
  semantica: [
    "Descenso del gradiente: técnica que minimiza una función de pérdida moviendo los pesos contra la pendiente local, fundamento del entrenamiento de redes neuronales modernas.",
    "Carlos resalta que en mini-batch SGD se obtiene un estimador ruidoso del gradiente real, lo que actúa como regularización implícita y mejora la generalización.",
    "Optimizadores adaptativos (Adam) combinan momentum y escalado por varianza, siendo el default razonable para deep learning supervisado.",
  ],
};

const scores: Record<RagConfig, number[]> = {
  fija: [0.81, 0.74, 0.68],
  semantica: [0.93, 0.89, 0.85],
};

export function getRagCitations(config: RagConfig): Citation[] {
  return base.map((b, i) => ({
    ...b,
    excerpt: excerpts[config][i],
    score: scores[config][i],
  }));
}
