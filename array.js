const array = [10,5,8,20,3];

// ordenar o array e trazer o 2 maior número;

const ordenado = array.sort((a,b => b-a));

const segundoMaior = ordenado[1];

console.log(segundoMaior);