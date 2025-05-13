from helper import  ask_without_streaming






while True:
  query=input('Enter your query: ').lower()
  if query=='exit' or query=='quit':

    break

  answer=ask_without_streaming(query)
  print(answer)
