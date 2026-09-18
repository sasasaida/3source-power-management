from app.llm.interpreter import interpret_operator_notes


notes = [
    "Please keep the facility clean."
]


result = interpret_operator_notes(notes)

print("\nRESULT:")
print(result)

print("\nTYPE:")
print(type(result))

print("\nINTERPRETATIONS:")

for interpretation in result.interpretations:
    print("\n---")
    print("Note index:", interpretation.note_index)
    print("Applies:", interpretation.applies)
    print("Directive:", interpretation.directive_type)
    print("Adjustment:", interpretation.structured_adjustment)
    print("Explanation:", interpretation.explanation)