const PENDING_CHAT_QUESTION_KEY = 'pending_chat_question'

export function setPendingChatQuestion(question: string) {
  const text = question.trim()
  if (!text) return
  sessionStorage.setItem(PENDING_CHAT_QUESTION_KEY, text)
}

export function consumePendingChatQuestion(): string {
  const value = sessionStorage.getItem(PENDING_CHAT_QUESTION_KEY) || ''
  sessionStorage.removeItem(PENDING_CHAT_QUESTION_KEY)
  return value.trim()
}

