export const resolveRequestedPage = (requestedPage, currentPage = 1) => {
  if (Number.isInteger(requestedPage) && requestedPage > 0) {
    return requestedPage
  }

  if (Number.isInteger(currentPage) && currentPage > 0) {
    return currentPage
  }

  return 1
}