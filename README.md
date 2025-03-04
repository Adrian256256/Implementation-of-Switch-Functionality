# Implementation-of-Switch-Functionality
Harea Teodor-Adrian 333CA
Tema 1 - RL - Implementare Switch

  Implementarea consta in completarea scheletului primit cu functionalitatile
unui switch.

  Structuri pentru stocarea datelor si utilizarea acestora:

->mac_table: un dictionar care contine perechi de forma (adresa_mac, interfata);
            aici stocheaza switch-ul corespondenta intre un port al acestuia si
            o adresa mac, pentru a sti unde sa trimita pachetele.
            Initial, mac_table este gol. Cand switch-ul primeste un pachet, retine
            adresa mac sursa (de unde provine pachetul) si portul pe care acesta a
            venit. Astfel, cand va trebui sa trimita un pachet la acea adresa mac,
            va sti pe ce port trebuie trimis.

->vlan_table: se citeste fisierul de configurare al switch-ului respectiv si se
            retin in acest dictionar perechile (nume_port, T/id-ul vlan).
            Daca portul este "trunk", se retine T. Daca portul este access,
            se retine id-ul vlan-ului din care face parte statia careia ii
            corespunde portul respectiv.

->stp_table: dictionar in care se retine daca portul este deschis (listening/designated)
            sau inchis (blocking). Acest dictionar este folosit in implementarea STP.

  Descriere funtionalitate: In main se creeaza dictionarele si variabilele necesare.
Se citeste din fisierul de config al switch-ului, se face procesul de initializare al
STP-ului din enunt. Se porneste un thread care va executa in paralel cu programul
trimiterea pachetelor de BPDU, daca este cazul. Acest thread ruleaza functia
"send_bdpu_every_sec", care implementeaza pseudocodul din enunt, trimitand un pachet
BPDU la fiecare 1 secunda, daca este cazul. Se foloseste struct.pack pentru a modifica
datele din human-readable in machine_readable si folosim int.from_bytes ca sa facem
procesul invers.
    Se porneste un "while True" care va tine switch-ul activ. In acest "while" se
proceseaza pachetele primite si se trimit/redirectioneaza pe porturile necesare.
    Prima daca verificam daca pachetul este BPDU pentru STP. Daca este, se realizeaza
implementarea pseudocodului si explicatiilor de la primirea pachetului BDPU.
    Daca nu avem pachet BPDU, switch-ul va trimite pachetul pe portul necesar. Se
salveaza in mac_table corespondenta dintre mac-ul sursa al pachetului primit si portul
pe care acesta a fost primit. Se verifica daca stim portul corespondent adresei mac
destinatie. Daca nu stim portul, vom trimite pachetul pe toate porturile deschise
(DESIGNATED_PORT). La trimiterea pachetului, se verifica daca este nevoie de adaugarea
unui vlan tag, sau daca e necesara scoaterea acestuia. Ne folosim de vlan_table pentru
verificarea faptului ca un port este TRUNK sau ACCESS. Tot de vlan_table ne folosim
pentru a face verificarea faptului ca o statie ACCESS nu primeste un pachet din alt
VLAN decat cel din care face parte aceasta.
