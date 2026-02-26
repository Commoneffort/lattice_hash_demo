import crypto from 'crypto';
import bigInt from 'big-integer';
import fs from 'fs';
import Dilithium from 'dilithium-crystals-js';

// Helper functions
function sha3(data) {
    return crypto.createHash('sha3-256').update(data).digest('hex');
}

// Lattice basis vectors for 3D space
const basis1 = [bigInt(3), bigInt(1), bigInt(4)];
const basis2 = [bigInt(2), bigInt(2), bigInt(1)];
const basis3 = [bigInt(1), bigInt(3), bigInt(2)];

// LWE Commitment Scheme
function lweCommitment(secret, noise, publicMatrix) {
    const result = [];
    for (let i = 0; i < publicMatrix.length; i++) {
        let sum = bigInt(0);
        for (let j = 0; j < secret.length; j++) {
            sum = sum.add(publicMatrix[i][j].multiply(secret[j]));
        }
        result.push(sum.add(noise[i]));
    }
    return result;
}

function lweVerifyCommitment(commitment, secret, noise, publicMatrix) {
    const result = [];
    for (let i = 0; i < publicMatrix.length; i++) {
        let sum = bigInt(0);
        for (let j = 0; j < secret.length; j++) {
            sum = sum.add(publicMatrix[i][j].multiply(secret[j]));
        }
        result.push(sum.add(noise[i]));
    }
    return result.every((value, index) => value.equals(commitment[index]));
}

// Generate lattice point based on player's random numbers in 3D space
function generateLatticePoint(random1, random2, random3) {
    const x = basis1[0].multiply(random1).add(basis2[0].multiply(random2)).add(basis3[0].multiply(random3));
    const y = basis1[1].multiply(random1).add(basis2[1].multiply(random2)).add(basis3[1].multiply(random3));
    const z = basis1[2].multiply(random1).add(basis2[2].multiply(random2)).add(basis3[2].multiply(random3));
    return { x, y, z };
}

// VDF computation (Wesolowski VDF)
function computeVDF(base, exponent, modulus) {
    let result = base;
    for (let i = 0; i < exponent; i++) {
        result = result.modPow(2, modulus);
    }
    return result;
}

function verifyVDF(base, exponent, modulus, result) {
    const verificationResult = base.modPow(bigInt(2).modPow(exponent, modulus.subtract(1)), modulus);
    return verificationResult.equals(result);
}

// Euclidean distance between two points in 3D space
function calculateDistance(point1, point2) {
    const dx = BigInt(point1.x) - BigInt(point2.x);
    const dy = BigInt(point1.y) - BigInt(point2.y);
    const dz = BigInt(point1.z) - BigInt(point2.z);
    const distanceSquared = dx ** BigInt(2) + dy ** BigInt(2) + dz ** BigInt(2);
    return Math.sqrt(Number(distanceSquared));
}

// Player class to manage random data, LWE commitments, VDF, and reveals
class Player {
    constructor(id, publicMatrix, dilithium) {
        this.id = id;
        this.secret = [bigInt.randBetween(1, 1000), bigInt.randBetween(1, 1000), bigInt.randBetween(1, 1000)];
        this.noise = [bigInt.randBetween(1, 100), bigInt.randBetween(1, 100), bigInt.randBetween(1, 100)];
        this.publicMatrix = publicMatrix;
        const { publicKey, privateKey } = dilithium.generateKeys(2);
       this.keyPair = { publicKey, privateKey };
        this.commitment = lweCommitment(this.secret, this.noise, this.publicMatrix);
        this.revealed = false;
        this.vdfResult = null;
        this.latticePoint = generateLatticePoint(this.secret[0], this.secret[1], this.secret[2]);
    }

    commit() {
        console.log(`Player ${this.id} committed with LWE commitment: ${this.commitment}`);
        return this.commitment;
    }

    computeAndSubmitVDF(exponent, modulus) {
        const sumSecret = this.secret.reduce((a, b) => a.add(b));
        this.vdfResult = computeVDF(sumSecret, exponent, modulus);
        return this.vdfResult;
    }

    verifyVDF(exponent, modulus) {
        const sumSecret = this.secret.reduce((a, b) => a.add(b));
        const isValid = verifyVDF(sumSecret, exponent, modulus, this.vdfResult);
        if (!isValid) {
            throw new Error(`Player ${this.id} VDF verification failed!`);
        }
        console.log(`Player ${this.id} VDF verified successfully.`);
    }

    reveal() {
        if (!lweVerifyCommitment(this.commitment, this.secret, this.noise, this.publicMatrix)) {
            throw new Error(`Player ${this.id} reveal does not match LWE commitment!`);
        }
        this.revealed = true;
        return { id: this.id, secret: this.secret, point: this.latticePoint };
    }
}

// Function to setup Dilithium
async function setupDilithium() {
    const dilithium = await Dilithium;
    return dilithium;
}

// Main function to simulate Lattice-based MPC protocol with LWE and VDF in 3D
async function simulateLatticeMPC(numPlayers = 10) {
    const dilithium = await setupDilithium();
    const players = [];
    const publicMatrix = [
        [bigInt(5), bigInt(7), bigInt(11)],
        [bigInt(3), bigInt(13), bigInt(19)],
        [bigInt(2), bigInt(17), bigInt(23)]
    ];

    for (let i = 1; i <= numPlayers; i++) {
        players.push(new Player(i, publicMatrix, dilithium));
    }

    console.log("\nCommit Phase:");
    players.forEach(player => player.commit());

    const exponent = 1000000;
    const modulus = bigInt(2).pow(256).subtract(189);
    console.log(`\nShared VDF parameters: exponent = ${exponent}, modulus = ${modulus}`);

    console.log("\nVDF Phase:");
    players.forEach(player => player.computeAndSubmitVDF(exponent, modulus));
    console.log("\nVDF Verification Phase:");
    players.forEach(player => {
        try {
            player.verifyVDF(exponent, modulus);
        } catch (error) {
            console.error(error.message);
        }
    });

    console.log("\nReveal Phase:");
    const playerData = players.map(player => {
    try {
       return player.reveal();
    } catch (error) {
        console.error(error.message);
    }
    }).filter(Boolean); // Filter out undefined values

    const minX = bigInt(Math.min(...playerData.map(data => data.point.x)));
    const maxX = bigInt(Math.max(...playerData.map(data => data.point.x)));
    const minY = bigInt(Math.min(...playerData.map(data => data.point.y)));
    const maxY = bigInt(Math.max(...playerData.map(data => data.point.y)));
    const minZ = bigInt(Math.min(...playerData.map(data => data.point.z)));
    const maxZ = bigInt(Math.max(...playerData.map(data => data.point.z)));

    console.log(`\nMin and Max Values after Reveal Phase:`);
    console.log(`minX: ${minX}, maxX: ${maxX}`);
    console.log(`minY: ${minY}, maxY: ${maxY}`);
    console.log(`minZ: ${minZ}, maxZ: ${maxZ}`);

    const combinedString = playerData.map(data => data.secret.join('')).join('');
    const hash = sha3(combinedString);
    console.log(`\nSHA-3 hash of combined string: ${hash}`);

    const hashAsInt = bigInt(hash, 16);
    console.log(`Hash as integer: ${hashAsInt}`);

    const compositePoint = {
        x: hashAsInt.mod(bigInt(minX.add(maxX))),
        y: hashAsInt.mod(bigInt(minY.add(maxY))),
        z: hashAsInt.mod(bigInt(minZ.add(maxZ)))
    };

    console.log(`\nComposite Lattice Hash-based point: (${compositePoint.x}, ${compositePoint.y}, ${compositePoint.z})`);

    const distances = playerData.map(data => ({
        id: data.id,
        distance: calculateDistance(data.point, compositePoint)
    }));

    distances.forEach(d => {
        console.log(`Player ${d.id} distance to Composite Point: ${d.distance}`);
    });

    const winner = distances.reduce((min, current) => (current.distance < min.distance ? current : min));
    console.log(`\nThe winner is Player ${winner.id}, with a distance of ${winner.distance} to the hash-based lattice point.`);

    // Generate HTML content with Plotly 3D Scatter Plot
    const htmlContent = `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>3D Scatter Plot of Lattice Points</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        </head>
        <body>
            <div id="scatter-plot" style="width: 100%; height: 100vh;"></div>
            <script>
                const data = [{
                    x: [${playerData.map(p => p.point.x).join(',')}],
                    y: [${playerData.map(p => p.point.y).join(',')}],
                    z: [${playerData.map(p => p.point.z).join(',')}],
                    mode: 'markers',
                    type: 'scatter3d'
                }];

                const layout = {
                    title: '3D Scatter Plot of Lattice Points',
                    scene: {
                        xaxis: { title: 'X-axis' },
                        yaxis: { title: 'Y-axis' },
                        zaxis: { title: 'Z-axis' }
                    }
                };

                Plotly.newPlot('scatter-plot', data, layout);
            </script>
        </body>
        </html>
    `;

    fs.writeFileSync('scatter_plot.html', htmlContent);
    console.log("HTML scatter plot generated: scatter_plot.html");
}

// Run the lattice-based simulation with LWE and VDF
simulateLatticeMPC();
